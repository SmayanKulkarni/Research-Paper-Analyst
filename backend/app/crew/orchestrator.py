import os
import time
from typing import Dict, List, Optional, Any
from crewai import Crew, Process

from app.config import get_settings
# Consolidated agents (reduced from 6 to 5 + vision)
from app.crew.agents.language_quality_agent import create_language_quality_agent
from app.crew.agents.structure_agent import create_structure_agent
from app.crew.agents.citation_agent import create_citation_agent
from app.crew.agents.plagiarism_agent import create_plagiarism_agent
from app.crew.agents.vision_agent import create_vision_agent
from app.crew.agents.math_agent import create_math_review_agent

# Consolidated tasks
from app.crew.tasks.language_quality_task import create_language_quality_task
from app.crew.tasks.structure_task import create_structure_task
from app.crew.tasks.citation_task import create_citation_task
from app.crew.tasks.plagiarism_task import create_plagiarism_task
from app.crew.tasks.vision_task import create_vision_task
from app.crew.tasks.math_task import create_math_review_task, detect_math_content, extract_math_content

from app.crew.tools.pdf_tool import load_pdf
from app.services.paper_discovery import PaperDiscoveryService
from app.services.image_extractor import extract_images_from_pdf
from app.services.pdf_report_generator import PDFReportGenerator
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
    
    ACCURACY-FIRST APPROACH (v4):
    - Dynamic token allocation based on actual PDF content
    - Each agent receives the full context it needs for thorough analysis
    - No arbitrary token limits - agents use what they need
    - Budget scales with document complexity (up to 300k tokens)
    - Math Review agent only runs if paper has mathematical content
    - Web search enabled for plagiarism detection
    - Structured final report compilation
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.token_usage = {
            "language_quality": 0,
            "structure": 0,
            "citation": 0,
            "plagiarism": 0,
            "math_review": 0,
            "vision": 0,
            "total_estimated": 0
        }
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text (roughly 4 chars = 1 token)."""
        return len(text) // self.settings.CHARS_PER_TOKEN
    
    def _calculate_token_budget(self, text: str, num_images: int, has_math: bool) -> Dict[str, int]:
        """
        Calculate token budget for each agent based on actual content.
        
        Strategy:
        - Base input: Full paper text tokens
        - Output: Proportional to task complexity
        - No artificial limits - accuracy is priority
        """
        text_tokens = self._estimate_tokens(text)
        
        # Log the paper stats
        logger.info(f"📊 Paper Analysis:")
        logger.info(f"   - Text length: {len(text):,} characters")
        logger.info(f"   - Estimated tokens: {text_tokens:,}")
        logger.info(f"   - Images: {num_images}")
        logger.info(f"   - Has math content: {has_math}")
        
        # Calculate per-agent budgets
        # Each agent needs: input (paper) + output (analysis)
        # Output size scales with paper complexity
        
        base_output = self.settings.MAX_COMPLETION_TOKENS  # 4096
        
        # Language Quality: Needs full text, produces detailed feedback
        # Output scales with paper length (more text = more potential issues)
        lang_output = min(base_output * 2, max(base_output, text_tokens // 10))
        
        # Structure: Needs full text for section analysis
        struct_output = base_output
        
        # Citation: Needs full text to find all citations
        # More citations in longer papers = more output
        cite_output = min(base_output * 2, max(base_output, text_tokens // 15))
        
        # Plagiarism: Needs full text for comprehensive check
        plag_output = base_output
        
        # Math: Only if detected, needs extracted math sections
        math_output = base_output if has_math else 0
        
        # Vision: Based on number of images
        vision_output = min(num_images * 500, self.settings.MAX_VISION_TOKENS * num_images // 5) if num_images > 0 else 0
        
        budget = {
            "language_quality": {
                "input": text_tokens,
                "output": lang_output,
                "total": text_tokens + lang_output
            },
            "structure": {
                "input": text_tokens,
                "output": struct_output,
                "total": text_tokens + struct_output
            },
            "citation": {
                "input": text_tokens,
                "output": cite_output,
                "total": text_tokens + cite_output
            },
            "plagiarism": {
                "input": text_tokens,
                "output": plag_output,
                "total": text_tokens + plag_output
            },
            "math_review": {
                "input": text_tokens // 3 if has_math else 0,  # Math sections ~1/3 of paper max
                "output": math_output,
                "total": (text_tokens // 3 + math_output) if has_math else 0
            },
            "vision": {
                "input": num_images * 1000,  # ~1k tokens per image
                "output": vision_output,
                "total": num_images * 1000 + vision_output
            }
        }
        
        # Calculate total
        total = sum(b["total"] for b in budget.values())
        budget["total_estimated"] = total
        
        logger.info(f"📈 Token Budget Allocation:")
        for agent, alloc in budget.items():
            if isinstance(alloc, dict):
                logger.info(f"   - {agent}: {alloc['total']:,} tokens (in: {alloc['input']:,}, out: {alloc['output']:,})")
            else:
                logger.info(f"   - {agent}: {alloc:,} tokens")
        
        return budget
    
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
        # ACCURACY-FIRST Agent Analysis Pipeline
        # Each agent works INDEPENDENTLY on the FULL paper
        # No text truncation - agents see everything
        # ---------------------------------------------------------
        
        full_text = text
        text_length = len(full_text)
        num_images = len(images) if images else 0
        
        # Detect math content early for budget calculation
        has_math = detect_math_content(full_text)
        
        # Calculate dynamic token budget based on actual content
        token_budget = self._calculate_token_budget(full_text, num_images, has_math)
        self.token_usage["total_estimated"] = token_budget["total_estimated"]
        
        logger.info(f"🎯 Total estimated token usage: {token_budget['total_estimated']:,} tokens")
        
        # Extract section headings for structure analysis (supplementary, not replacement)
        section_headings = self._extract_section_headings(full_text)

        # ---------------------------------------------------------
        # Create Agents with Dynamic Token Allocation
        # Each agent gets tokens based on its specific needs
        # ---------------------------------------------------------
        lang_tokens = token_budget["language_quality"]["output"]
        struct_tokens = token_budget["structure"]["output"]
        cite_tokens = token_budget["citation"]["output"]
        plag_tokens = token_budget["plagiarism"]["output"]
        
        language_agent = create_language_quality_agent(max_tokens=lang_tokens)
        structure_agent = create_structure_agent(max_tokens=struct_tokens)
        citation_agent = create_citation_agent(max_tokens=cite_tokens) if enable_citation else None
        plagiarism_agent = create_plagiarism_agent(max_tokens=plag_tokens) if enable_plagiarism else None

        # ---------------------------------------------------------
        # Run Tasks INDIVIDUALLY with rate limiting
        # This avoids hitting Groq's strict rate limits
        # ---------------------------------------------------------
        structured_results = {}
        structured_results["token_budget"] = token_budget  # Include budget info in results
        rate_limit_delay = self.settings.RATE_LIMIT_DELAY
        
        # Task 1: Language Quality (FULL paper text - no truncation)
        logger.info(f"🔍 Running Language Quality analysis (budget: {lang_tokens:,} output tokens)...")
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
        
        # Task 2: Structure (FULL paper text + headings for reference)
        logger.info(f"🔍 Running Structure analysis (budget: {struct_tokens:,} output tokens)...")
        try:
            struct_crew = Crew(
                agents=[structure_agent],
                tasks=[create_structure_task(structure_agent, full_text, section_headings)],
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
        
        # Task 3: Citation (if enabled) - FULL paper text
        if citation_agent:
            logger.info(f"🔍 Running Citation analysis (budget: {cite_tokens:,} output tokens)...")
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
        
        # Task 4: Plagiarism (if enabled) - FULL paper with web search
        if plagiarism_agent:
            logger.info(f"🔍 Running Plagiarism analysis with web search (budget: {plag_tokens:,} output tokens)...")
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
            
            time.sleep(rate_limit_delay)
        
        # Task 5: Math Review (only if paper has mathematical content)
        # Note: has_math was already calculated during budget calculation
        if has_math:
            math_tokens = token_budget["math_review"]["output"]
            logger.info(f"🔍 Mathematical content detected. Running Math Review (budget: {math_tokens:,} output tokens)...")
            try:
                math_content = extract_math_content(full_text)
                math_agent = create_math_review_agent()
                math_task = create_math_review_task(math_agent, math_content)
                
                math_crew = Crew(
                    agents=[math_agent],
                    tasks=[math_task],
                    process=Process.sequential,
                    verbose=True,
                    memory=False,
                )
                math_result = run_with_retry(
                    math_crew.kickoff,
                    max_retries=self.settings.MAX_RETRIES,
                    retry_delay=self.settings.RETRY_DELAY
                )
                structured_results["math_review"] = str(math_result)
                logger.info("✅ Math Review analysis complete")
            except Exception as e:
                logger.error(f"Math Review analysis failed: {e}")
                structured_results["math_review"] = f"Analysis failed: {str(e)[:100]}"
            
            time.sleep(rate_limit_delay)
        else:
            logger.info("No significant mathematical content detected. Skipping Math Review.")
            structured_results["math_review"] = None

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

        # ---------------------------------------------------------
        # Generate Structured Final Report
        # ---------------------------------------------------------
        logger.info("Generating structured final report...")
        final_report = self._compile_final_report(structured_results)
        structured_results["final_report"] = final_report
        
        # ---------------------------------------------------------
        # Generate PDF Report
        # ---------------------------------------------------------
        logger.info("Generating PDF report...")
        try:
            pdf_generator = PDFReportGenerator()
            pdf_path = pdf_generator.generate_report(
                results=structured_results,
                file_id=log_id
            )
            structured_results["pdf_report_path"] = pdf_path
            logger.info(f"✅ PDF report saved to: {pdf_path}")
        except Exception as e:
            logger.error(f"PDF report generation failed: {e}")
            structured_results["pdf_report_path"] = None
        
        logger.info("🎉 All analysis complete!")
        return structured_results
    
    def _compile_final_report(self, results: Dict[str, Any]) -> str:
        """
        Compile all agent outputs into a well-structured final report.
        
        This creates a comprehensive analysis document that synthesizes
        findings from all agents into a coherent paper review.
        """
        sections = []
        
        # Title
        sections.append("# Research Paper Analysis Report\n")
        sections.append("---\n")
        
        # Executive Summary
        sections.append("## Executive Summary\n")
        summary_points = []
        
        # Summarize each section's key finding
        if results.get("language_quality") and "failed" not in results["language_quality"].lower():
            summary_points.append("- **Language Quality**: Analysis completed")
        if results.get("structure") and "failed" not in results["structure"].lower():
            summary_points.append("- **Structure**: Analysis completed")
        if results.get("citations") and "failed" not in results["citations"].lower():
            summary_points.append("- **Citations**: Analysis completed")
        if results.get("plagiarism") and "failed" not in results["plagiarism"].lower():
            summary_points.append("- **Plagiarism**: Analysis completed")
        if results.get("math_review") and "failed" not in str(results["math_review"]).lower():
            summary_points.append("- **Mathematical Content**: Analysis completed")
        if results.get("vision") and "failed" not in str(results["vision"]).lower():
            summary_points.append("- **Visual Elements**: Analysis completed")
        
        if summary_points:
            sections.append("\n".join(summary_points))
        else:
            sections.append("Analysis encountered issues. See individual sections for details.")
        sections.append("\n\n---\n")
        
        # Language Quality Section
        sections.append("## 1. Language Quality Analysis\n")
        sections.append("*Grammar, clarity, style, and consistency review*\n\n")
        if results.get("language_quality"):
            sections.append(str(results["language_quality"]))
        else:
            sections.append("*Analysis not available*")
        sections.append("\n\n---\n")
        
        # Structure Section
        sections.append("## 2. Paper Structure Analysis\n")
        sections.append("*Organization, section flow, and completeness*\n\n")
        if results.get("structure"):
            sections.append(str(results["structure"]))
        else:
            sections.append("*Analysis not available*")
        sections.append("\n\n---\n")
        
        # Citation Section
        sections.append("## 3. Citation Analysis\n")
        sections.append("*Reference verification and citation quality*\n\n")
        if results.get("citations"):
            sections.append(str(results["citations"]))
        else:
            sections.append("*Citation analysis was not enabled or not available*")
        sections.append("\n\n---\n")
        
        # Plagiarism Section
        sections.append("## 4. Plagiarism Check\n")
        sections.append("*Originality assessment via vector similarity and web search*\n\n")
        if results.get("plagiarism"):
            sections.append(str(results["plagiarism"]))
        else:
            sections.append("*Plagiarism analysis was not enabled or not available*")
        sections.append("\n\n---\n")
        
        # Math Review Section (conditional)
        if results.get("math_review"):
            sections.append("## 5. Mathematical Content Review\n")
            sections.append("*Equation correctness, proofs, and notation*\n\n")
            sections.append(str(results["math_review"]))
            sections.append("\n\n---\n")
        
        # Vision Section (conditional)
        if results.get("vision"):
            section_num = 6 if results.get("math_review") else 5
            sections.append(f"## {section_num}. Visual Elements Analysis\n")
            sections.append("*Figures, charts, and image quality assessment*\n\n")
            sections.append(str(results["vision"]))
            sections.append("\n\n---\n")
        
        # Footer
        sections.append("\n*Report generated by Research Paper Analyst*\n")
        
        return "\n".join(sections)

# Wrapper function to maintain backward compatibility with run_analysis.py
def run_full_analysis(
    file_id: str = None,
    text: str = None,
    images: list = None,
    pdf_path: str = None,
    enable_plagiarism: bool = True,
    enable_vision: bool = True,
    enable_citation: bool = True,
    enable_math: bool = True,  # Math review enabled by default (auto-detects if needed)
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