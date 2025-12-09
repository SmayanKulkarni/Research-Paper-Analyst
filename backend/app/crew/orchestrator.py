import os
import time
from typing import Dict, List, Optional, Any
from crewai import Crew, Process

from app.config import get_settings
# Consolidated agents (reduced from 6 to 4 + vision)
from app.crew.agents.language_quality_agent import create_language_quality_agent
from app.crew.agents.structure_agent import create_structure_agent
from app.crew.agents.citation_agent import create_citation_agent
from app.crew.agents.plagiarism_agent import create_plagiarism_agent
from app.crew.agents.vision_agent import create_vision_agent

# Consolidated tasks
from app.crew.tasks.language_quality_task import create_language_quality_task
from app.crew.tasks.structure_task import create_structure_task
from app.crew.tasks.citation_task import create_citation_task
from app.crew.tasks.plagiarism_task import create_plagiarism_task
from app.crew.tasks.vision_task import create_vision_task

from app.crew.tools.pdf_tool import load_pdf
from app.services.paper_discovery import PaperDiscoveryService
from app.services.image_extractor import extract_images_from_pdf
from app.utils.logging import logger

settings = get_settings()


def run_with_retry(func, *args, max_retries=1, retry_delay=5.0, **kwargs):
    """
    Run a function with minimal retry logic - fail fast approach.
    Only retry once for rate limits, otherwise fail immediately.
    """
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            # Only retry on rate limit (429) errors
            if ("429" in error_str or "rate" in error_str) and attempt < max_retries:
                logger.warning(f"Rate limit hit. Waiting {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                # For all other errors (including empty responses), fail immediately
                logger.error(f"Task failed: {str(e)[:100]}")
                raise


class AnalysisOrchestratorService:
    """
    Service responsible for orchestrating the CrewAI analysis pipeline.
    
    OPTIMIZATIONS (v2):
    - Consolidated 6 agents → 4+1 (Language Quality replaces Proofreader + Consistency)
    - Each agent works INDEPENDENTLY on FULL paper (no sequential output dependencies)
    - Dynamic token allocation based on paper length
    - Vision agent receives ONLY images (no text)
    """
    
    def __init__(self):
        self.settings = get_settings()
    
    def _calculate_dynamic_tokens(self, text_length: int, num_agents: int) -> int:
        """
        Calculate dynamic token allocation per agent based on paper length.
        
        Strategy:
        - Shorter papers: More tokens per agent for detailed analysis
        - Longer papers: Balanced tokens to stay within budget
        - Minimum 512 tokens, Maximum 2048 tokens per agent
        """
        # Estimate input tokens (rough: 4 chars ≈ 1 token)
        estimated_input_tokens = text_length // 4
        
        # Base output tokens from settings
        base_tokens = self.settings.MAX_COMPLETION_TOKENS
        
        # If paper is short (< 10k tokens), allow more detailed output
        if estimated_input_tokens < 10000:
            return min(2048, base_tokens * 2)
        
        # For longer papers, use base allocation
        # But ensure minimum useful output
        return max(512, base_tokens)
    
    def _extract_section_headings(self, text: str) -> str:
        """
        Extract section headings from paper for structure analysis.
        This allows structure agent to analyze organization without full text.
        """
        lines = text.split('\n')
        headings = []
        
        # Common section keywords in research papers
        section_keywords = [
            'abstract', 'introduction', 'background', 'related work',
            'methodology', 'methods', 'approach', 'experiments',
            'results', 'discussion', 'conclusion', 'future work',
            'references', 'appendix', 'acknowledgments'
        ]
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            # Check if line looks like a heading
            if any(kw in line_lower for kw in section_keywords):
                headings.append(f"Line {i+1}: {line.strip()}")
            # Also check for numbered sections like "1. Introduction"
            elif line.strip() and len(line.strip()) < 100:
                if line.strip()[0].isdigit() or line.strip().isupper():
                    headings.append(f"Line {i+1}: {line.strip()}")
        
        if headings:
            return "\n".join(headings[:50])  # Limit to 50 headings
        return "No clear section headings detected. Please analyze paper structure."

    def run_analysis(
        self,
        file_id: str = None,
        text: str = None,
        images: list = None,
        pdf_path: str = None,
        enable_plagiarism: bool = True,
        enable_vision: bool = True,
        enable_citation: bool = True,
    ) -> Dict[str, Any]:
        
        # 1. Determine Data Source
        if text is None:
            if file_id is None:
                raise ValueError("Either file_id or text must be provided")
            logger.info(f"Loading PDF data for file_id: {file_id}")
            pdf_data = load_pdf(file_id)
            text = pdf_data["text"]
            images = pdf_data["images"]
        else:
            if images is None:
                images = []

        log_id = file_id or "direct_input"
        logger.info(f"Starting pipeline for {log_id}")

        # ---------------------------------------------------------
        # Extract images from PDF for vision analysis
        # ---------------------------------------------------------
        if enable_vision and pdf_path and os.path.exists(pdf_path):
            logger.info(f"Extracting top 10 largest images from PDF for vision analysis...")
            try:
                images = extract_images_from_pdf(
                    pdf_path=pdf_path,
                    max_images=10,
                    min_width=100,
                    min_height=100,
                )
                logger.info(f"Extracted {len(images)} significant images for analysis")
            except Exception as e:
                logger.warning(f"Image extraction failed: {e}")
                images = []

        # ---------------------------------------------------------
        # Paper Discovery & Knowledge Base Update
        # ---------------------------------------------------------
        if file_id:
            try:
                # Construct path to the uploaded PDF file
                uploads_dir = os.path.join(self.settings.STORAGE_ROOT, self.settings.UPLOADS_DIR)
                pdf_path = os.path.join(uploads_dir, f"{file_id}.pdf")
                
                if os.path.exists(pdf_path):
                    logger.info(f"Running Paper Discovery Service for {file_id}...")
                    discovery_service = PaperDiscoveryService()
                    discovery_service.find_similar_papers(pdf_path)
                else:
                    logger.warning(f"PDF file not found at {pdf_path}, skipping discovery step.")
            except Exception as e:
                logger.error(f"Paper Discovery failed (continuing with analysis): {e}")

        # ---------------------------------------------------------
        # OPTIMIZED Agent Analysis Pipeline
        # Each agent works INDEPENDENTLY on the FULL paper
        # ---------------------------------------------------------
        
        full_text = text
        text_length = len(full_text)
        
        # Calculate dynamic tokens based on paper length
        # Count active agents: language_quality + structure + citation? + plagiarism?
        num_agents = 2 + (1 if enable_citation else 0) + (1 if enable_plagiarism else 0)
        dynamic_tokens = self._calculate_dynamic_tokens(text_length, num_agents)
        
        logger.info(f"Paper length: {text_length} chars, Dynamic tokens per agent: {dynamic_tokens}")
        
        # Extract section headings for structure analysis (reduces token usage)
        section_headings = self._extract_section_headings(full_text)

        # ---------------------------------------------------------
        # Create Consolidated Agents (4 instead of 6)
        # ---------------------------------------------------------
        language_agent = create_language_quality_agent(max_tokens=dynamic_tokens)
        structure_agent = create_structure_agent(max_tokens=dynamic_tokens)
        citation_agent = create_citation_agent(max_tokens=dynamic_tokens) if enable_citation else None
        plagiarism_agent = create_plagiarism_agent(max_tokens=dynamic_tokens) if enable_plagiarism else None

        # ---------------------------------------------------------
        # Run Tasks INDIVIDUALLY with rate limiting
        # This avoids hitting Groq's strict rate limits
        # ---------------------------------------------------------
        structured_results = {}
        rate_limit_delay = self.settings.RATE_LIMIT_DELAY
        
        # Task 1: Language Quality
        logger.info("Running Language Quality analysis...")
        try:
            lang_crew = Crew(
                agents=[language_agent],
                tasks=[create_language_quality_task(language_agent, full_text)],
                process=Process.sequential,
                verbose=True,
                memory=False,
            )
            lang_result = run_with_retry(
                lang_crew.kickoff,
                max_retries=self.settings.MAX_RETRIES,
                retry_delay=self.settings.RETRY_DELAY
            )
            structured_results["language_quality"] = str(lang_result)
            logger.info("✅ Language Quality analysis complete")
        except Exception as e:
            logger.error(f"Language Quality failed: {e}")
            structured_results["language_quality"] = f"Analysis failed: {str(e)[:100]}"
        
        # Rate limit delay
        logger.info(f"Waiting {rate_limit_delay}s for rate limit...")
        time.sleep(rate_limit_delay)
        
        # Task 2: Structure
        logger.info("Running Structure analysis...")
        try:
            struct_crew = Crew(
                agents=[structure_agent],
                tasks=[create_structure_task(structure_agent, section_headings)],
                process=Process.sequential,
                verbose=True,
                memory=False,
            )
            struct_result = run_with_retry(
                struct_crew.kickoff,
                max_retries=self.settings.MAX_RETRIES,
                retry_delay=self.settings.RETRY_DELAY
            )
            structured_results["structure"] = str(struct_result)
            logger.info("✅ Structure analysis complete")
        except Exception as e:
            logger.error(f"Structure analysis failed: {e}")
            structured_results["structure"] = f"Analysis failed: {str(e)[:100]}"
        
        # Rate limit delay
        time.sleep(rate_limit_delay)
        
        # Task 3: Citation (if enabled)
        if citation_agent:
            logger.info("Running Citation analysis...")
            try:
                cite_crew = Crew(
                    agents=[citation_agent],
                    tasks=[create_citation_task(citation_agent, full_text)],
                    process=Process.sequential,
                    verbose=True,
                    memory=False,
                )
                cite_result = run_with_retry(
                    cite_crew.kickoff,
                    max_retries=self.settings.MAX_RETRIES,
                    retry_delay=self.settings.RETRY_DELAY
                )
                structured_results["citations"] = str(cite_result)
                logger.info("✅ Citation analysis complete")
            except Exception as e:
                logger.error(f"Citation analysis failed: {e}")
                structured_results["citations"] = f"Analysis failed: {str(e)[:100]}"
            
            time.sleep(rate_limit_delay)
        
        # Task 4: Plagiarism (if enabled)
        if plagiarism_agent:
            logger.info("Running Plagiarism analysis...")
            try:
                plag_crew = Crew(
                    agents=[plagiarism_agent],
                    tasks=[create_plagiarism_task(plagiarism_agent, full_text)],
                    process=Process.sequential,
                    verbose=True,
                    memory=False,
                )
                plag_result = run_with_retry(
                    plag_crew.kickoff,
                    max_retries=self.settings.MAX_RETRIES,
                    retry_delay=self.settings.RETRY_DELAY
                )
                structured_results["plagiarism"] = str(plag_result)
                logger.info("✅ Plagiarism analysis complete")
            except Exception as e:
                logger.error(f"Plagiarism analysis failed: {e}")
                structured_results["plagiarism"] = f"Analysis failed: {str(e)[:100]}"

        # ---------------------------------------------------------
        # Run Vision Analysis (Separate Crew - IMAGES ONLY)
        # ---------------------------------------------------------
        if enable_vision and images:
            time.sleep(rate_limit_delay)
            logger.info(f"Running vision analysis on {len(images)} images...")
            try:
                vision_agent = create_vision_agent()
                vision_task = create_vision_task(vision_agent, images)

                vision_crew = Crew(
                    agents=[vision_agent],
                    tasks=[vision_task],
                    process=Process.sequential,
                    verbose=True,
                    memory=False,
                )

                vision_result = run_with_retry(
                    vision_crew.kickoff,
                    max_retries=self.settings.MAX_RETRIES,
                    retry_delay=self.settings.RETRY_DELAY
                )
                structured_results["vision"] = str(vision_result)
                logger.info("✅ Vision analysis complete")
            except Exception as e:
                logger.warning(f"Vision analysis failed: {e}")
                structured_results["vision"] = f"Analysis failed: {str(e)[:100]}"
        else:
            structured_results["vision"] = None

        logger.info("🎉 All analysis complete!")
        return structured_results

# Wrapper function to maintain backward compatibility with run_analysis.py
def run_full_analysis(
    file_id: str = None,
    text: str = None,
    images: list = None,
    pdf_path: str = None,
    enable_plagiarism: bool = True,
    enable_vision: bool = True,
    enable_citation: bool = True,
):
    service = AnalysisOrchestratorService()
    return service.run_analysis(
        file_id=file_id,
        text=text,
        images=images,
        pdf_path=pdf_path,
        enable_plagiarism=enable_plagiarism,
        enable_vision=enable_vision,
        enable_citation=enable_citation
    )