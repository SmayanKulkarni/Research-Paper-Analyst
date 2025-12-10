import os
import time
from typing import Dict, List, Optional, Any
from crewai import Crew, Process

from app.config import get_settings
from app.crew.agents.language_quality_agent import create_language_quality_agent
from app.crew.agents.structure_agent import create_structure_agent
from app.crew.agents.citation_agent import create_citation_agent
from app.crew.agents.vision_agent import create_vision_agent
from app.crew.agents.math_agent import create_math_review_agent

from app.crew.tasks.language_quality_task import create_language_quality_task
from app.crew.tasks.structure_task import create_structure_task
from app.crew.tasks.citation_task import create_citation_task
from app.crew.tasks.vision_task import create_vision_task
from app.crew.tasks.math_task import create_math_review_task, detect_math_content, extract_math_content

from app.crew.tools.pdf_tool import load_pdf
from app.services.paper_discovery import PaperDiscoveryService
from app.services.image_extractor import extract_images_from_pdf
from app.services.pdf_report_generator import PDFReportGenerator
from app.utils.logging import logger

settings = get_settings()


def run_with_retry(func, *args, max_retries=1, retry_delay=5.0, **kwargs):
    """Run a function with minimal retry logic - fail fast approach."""
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            if ("429" in error_str or "rate" in error_str) and attempt < max_retries:
                logger.warning(f"Rate limit hit. Waiting {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Task failed: {str(e)[:100]}")
                raise


class AnalysisOrchestratorService:
    """Service responsible for orchestrating the CrewAI analysis pipeline."""
    
    def __init__(self):
        self.settings = get_settings()
        self.token_usage = {
            "language_quality": 0, "structure": 0, "citation": 0,
            "math_review": 0, "vision": 0, "plagiarism": 0, "total_estimated": 0
        }
    
    def _estimate_tokens(self, text: str) -> int:
        return len(text) // self.settings.CHARS_PER_TOKEN
    
    def _calculate_token_budget(self, text: str, num_images: int, has_math: bool) -> Dict[str, int]:
        text_tokens = self._estimate_tokens(text)
        
        logger.info(f"📊 Paper Analysis: {len(text):,} chars, {text_tokens:,} tokens, {num_images} images, math={has_math}")
        
        base_output = self.settings.MAX_COMPLETION_TOKENS
        
        budget = {
            "language_quality": {"input": text_tokens, "output": min(base_output * 2, max(base_output, text_tokens // 10)), "total": 0},
            "structure": {"input": text_tokens, "output": base_output, "total": 0},
            "citation": {"input": text_tokens, "output": min(base_output * 2, max(base_output, text_tokens // 15)), "total": 0},
            "math_review": {"input": text_tokens // 3 if has_math else 0, "output": base_output if has_math else 0, "total": 0},
            "vision": {"input": num_images * 1000, "output": min(num_images * 500, 4096) if num_images > 0 else 0, "total": 0},
            "plagiarism": {"input": 2000, "output": base_output, "total": 0}
        }
        
        for key in budget:
            budget[key]["total"] = budget[key]["input"] + budget[key]["output"]
        
        budget["total_estimated"] = sum(b["total"] for b in budget.values() if isinstance(b, dict))
        return budget
    
    def _extract_section_headings(self, text: str) -> str:
        lines = text.split('\n')
        headings = []
        section_keywords = ['abstract', 'introduction', 'background', 'related work', 'methodology', 
                           'methods', 'approach', 'experiments', 'results', 'discussion', 
                           'conclusion', 'future work', 'references', 'appendix']
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            if any(kw in line_lower for kw in section_keywords):
                headings.append(f"Line {i+1}: {line.strip()}")
            elif line.strip() and len(line.strip()) < 100:
                if line.strip()[0].isdigit() or line.strip().isupper():
                    headings.append(f"Line {i+1}: {line.strip()}")
        
        return "\n".join(headings[:50]) if headings else "No clear section headings detected."

    def run_analysis(
        self,
        file_id: str = None,
        text: str = None,
        images: list = None,
        pdf_path: str = None,
        enable_vision: bool = True,
        enable_citation: bool = True,
        enable_plagiarism: bool = True,
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

        # Extract images from PDF
        if enable_vision and pdf_path and os.path.exists(pdf_path):
            logger.info("Extracting images from PDF...")
            try:
                images = extract_images_from_pdf(pdf_path=pdf_path, max_images=10, min_width=100, min_height=100)
                logger.info(f"Extracted {len(images)} images")
            except Exception as e:
                logger.warning(f"Image extraction failed: {e}")
                images = []

        # Paper Discovery
        if file_id:
            try:
                uploads_dir = os.path.join(self.settings.STORAGE_ROOT, self.settings.UPLOADS_DIR)
                pdf_path = os.path.join(uploads_dir, f"{file_id}.pdf")
                if os.path.exists(pdf_path):
                    logger.info(f"Running Paper Discovery...")
                    PaperDiscoveryService().find_similar_papers(pdf_path)
            except Exception as e:
                logger.error(f"Paper Discovery failed: {e}")

        # Setup
        full_text = text
        num_images = len(images) if images else 0
        has_math = detect_math_content(full_text)
        token_budget = self._calculate_token_budget(full_text, num_images, has_math)
        section_headings = self._extract_section_headings(full_text)
        
        lang_tokens = token_budget["language_quality"]["output"]
        struct_tokens = token_budget["structure"]["output"]
        cite_tokens = token_budget["citation"]["output"]
        
        language_agent = create_language_quality_agent(max_tokens=lang_tokens)
        structure_agent = create_structure_agent(max_tokens=struct_tokens)
        citation_agent = create_citation_agent(max_tokens=cite_tokens) if enable_citation else None

        structured_results = {"token_budget": token_budget}
        rate_limit_delay = self.settings.RATE_LIMIT_DELAY
        
        # Task 1: Language Quality
        logger.info(f"🔍 Running Language Quality analysis...")
        try:
            lang_crew = Crew(
                agents=[language_agent],
                tasks=[create_language_quality_task(language_agent, full_text)],
                process=Process.sequential, verbose=True, memory=False,
            )
            lang_result = run_with_retry(lang_crew.kickoff, max_retries=1, retry_delay=5)
            structured_results["language_quality"] = str(lang_result)
            logger.info("✅ Language Quality complete")
        except Exception as e:
            logger.error(f"Language Quality failed: {e}")
            structured_results["language_quality"] = f"Analysis failed: {str(e)[:100]}"
        
        time.sleep(rate_limit_delay)
        
        # Task 2: Structure
        logger.info(f"🔍 Running Structure analysis...")
        try:
            struct_crew = Crew(
                agents=[structure_agent],
                tasks=[create_structure_task(structure_agent, full_text, section_headings)],
                process=Process.sequential, verbose=True, memory=False,
            )
            struct_result = run_with_retry(struct_crew.kickoff, max_retries=1, retry_delay=5)
            structured_results["structure"] = str(struct_result)
            logger.info("✅ Structure complete")
        except Exception as e:
            logger.error(f"Structure failed: {e}")
            structured_results["structure"] = f"Analysis failed: {str(e)[:100]}"
        
        time.sleep(rate_limit_delay)
        
        # Task 3: Citation
        if citation_agent:
            logger.info(f"🔍 Running Citation analysis...")
            try:
                cite_crew = Crew(
                    agents=[citation_agent],
                    tasks=[create_citation_task(citation_agent, full_text)],
                    process=Process.sequential, verbose=True, memory=False,
                )
                cite_result = run_with_retry(cite_crew.kickoff, max_retries=1, retry_delay=5)
                structured_results["citations"] = str(cite_result)
                logger.info("✅ Citation complete")
            except Exception as e:
                logger.error(f"Citation failed: {e}")
                structured_results["citations"] = f"Analysis failed: {str(e)[:100]}"
            time.sleep(rate_limit_delay)
        
        # Task 4: Math Review
        if has_math:
            logger.info(f"🔍 Running Math Review...")
            try:
                math_content = extract_math_content(full_text)
                math_agent = create_math_review_agent()
                math_task = create_math_review_task(math_agent, math_content)
                math_crew = Crew(
                    agents=[math_agent], tasks=[math_task],
                    process=Process.sequential, verbose=True, memory=False,
                )
                math_result = run_with_retry(math_crew.kickoff, max_retries=1, retry_delay=5)
                structured_results["math_review"] = str(math_result)
                logger.info("✅ Math Review complete")
            except Exception as e:
                logger.error(f"Math Review failed: {e}")
                structured_results["math_review"] = f"Analysis failed: {str(e)[:100]}"
            time.sleep(rate_limit_delay)
        else:
            structured_results["math_review"] = None

        # Task 5: Plagiarism Check (Direct OpenAlex API - No LLM needed)
        if enable_plagiarism:
            logger.info("🔍 Running Plagiarism analysis (direct OpenAlex)...")
            try:
                from app.crew.tools.semantic_scholar_tool import run_plagiarism_search
                plagiarism_result = run_plagiarism_search(full_text)
                structured_results["plagiarism"] = plagiarism_result
                logger.info("✅ Plagiarism complete (direct API)")
            except Exception as e:
                logger.error(f"Plagiarism failed: {e}")
                structured_results["plagiarism"] = f"Analysis failed: {str(e)[:100]}"
        else:
            structured_results["plagiarism"] = None

        # Task 6: Vision Analysis
        if enable_vision and images:
            time.sleep(rate_limit_delay)
            logger.info(f"🔍 Running Vision analysis on {len(images)} images...")
            try:
                vision_agent = create_vision_agent()
                vision_task = create_vision_task(vision_agent, images)
                vision_crew = Crew(
                    agents=[vision_agent], tasks=[vision_task],
                    process=Process.sequential, verbose=True, memory=False,
                )
                vision_result = run_with_retry(vision_crew.kickoff, max_retries=1, retry_delay=5)
                structured_results["vision"] = str(vision_result)
                logger.info("✅ Vision complete")
            except Exception as e:
                logger.warning(f"Vision failed: {e}")
                structured_results["vision"] = f"Analysis failed: {str(e)[:100]}"
        else:
            structured_results["vision"] = None

        # Generate Reports
        logger.info("Generating structured final report...")
        structured_results["final_report"] = self._compile_final_report(structured_results)
        
        logger.info("Generating PDF report...")
        try:
            pdf_generator = PDFReportGenerator()
            pdf_path = pdf_generator.generate_report(results=structured_results, file_id=log_id)
            structured_results["pdf_report_path"] = pdf_path
            logger.info(f"✅ PDF report saved to: {pdf_path}")
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            structured_results["pdf_report_path"] = None
        
        logger.info("🎉 All analysis complete!")
        return structured_results
    
    def _compile_final_report(self, results: Dict[str, Any]) -> str:
        sections = ["# Research Paper Analysis Report\n", "---\n", "## Executive Summary\n"]
        
        summary = []
        for key, label in [("language_quality", "Language Quality"), ("structure", "Structure"), 
                           ("citations", "Citations"), ("math_review", "Math"), 
                           ("plagiarism", "Plagiarism"), ("vision", "Visual Elements")]:
            if results.get(key) and "failed" not in str(results[key]).lower():
                summary.append(f"- **{label}**: Analysis completed")
        
        sections.append("\n".join(summary) if summary else "Analysis encountered issues.")
        sections.append("\n\n---\n")
        
        # Sections
        sections.append("## 1. Language Quality Analysis\n")
        sections.append(str(results.get("language_quality", "*Not available*")))
        sections.append("\n\n---\n")
        
        sections.append("## 2. Paper Structure Analysis\n")
        sections.append(str(results.get("structure", "*Not available*")))
        sections.append("\n\n---\n")
        
        sections.append("## 3. Citation Analysis\n")
        sections.append(str(results.get("citations", "*Not available*")))
        sections.append("\n\n---\n")
        
        section_num = 4
        if results.get("math_review"):
            sections.append(f"## {section_num}. Mathematical Content Review\n")
            sections.append(str(results["math_review"]))
            sections.append("\n\n---\n")
            section_num += 1
        
        if results.get("plagiarism"):
            sections.append(f"## {section_num}. Plagiarism & Originality Check\n")
            sections.append(str(results["plagiarism"]))
            sections.append("\n\n---\n")
            section_num += 1
        
        if results.get("vision"):
            sections.append(f"## {section_num}. Visual Elements Analysis\n")
            sections.append(str(results["vision"]))
            sections.append("\n\n---\n")
        
        sections.append("\n*Report generated by Research Paper Analyst*\n")
        return "\n".join(sections)


def run_full_analysis(
    file_id: str = None, text: str = None, images: list = None, pdf_path: str = None,
    enable_vision: bool = True, enable_citation: bool = True, enable_plagiarism: bool = True,
    enable_math: bool = True,
):
    service = AnalysisOrchestratorService()
    return service.run_analysis(
        file_id=file_id, text=text, images=images, pdf_path=pdf_path,
        enable_vision=enable_vision, enable_citation=enable_citation, enable_plagiarism=enable_plagiarism
    )