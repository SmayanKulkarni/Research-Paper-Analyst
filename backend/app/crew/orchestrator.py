import os
from typing import Dict, List, Optional, Any
from crewai import Crew, Process

from app.config import get_settings
from app.crew.agents.proofreader_agent import create_proofreader
from app.crew.agents.structure_agent import create_structure_agent
from app.crew.agents.citation_agent import create_citation_agent
from app.crew.agents.consistency_agent import create_consistency_agent
from app.crew.agents.vision_agent import create_vision_agent
from app.crew.agents.plagiarism_agent import create_plagiarism_agent

from app.crew.tasks.proofreading_task import create_proofreading_task
from app.crew.tasks.structure_task import create_structure_task
from app.crew.tasks.citation_task import create_citation_task
from app.crew.tasks.consistency_task import create_consistency_task
from app.crew.tasks.vision_task import create_vision_task
from app.crew.tasks.plagiarism_task import create_plagiarism_task

from app.crew.tools.pdf_tool import load_pdf
from app.services.paper_discovery import PaperDiscoveryService
from app.utils.logging import logger

settings = get_settings()


class AnalysisOrchestratorService:
    """
    Service responsible for orchestrating the CrewAI analysis pipeline.
    """
    
    def __init__(self):
        self.settings = get_settings()
        
    def _truncate_text_for_8b_model(self, text: str, max_chars: int = 15000) -> str:
        """
        Truncate text to avoid Rate Limits on smaller models (e.g., Llama 3.1 8B).
        
        The Llama 3.1 8B Instant model on Groq Free/On-Demand often has a 6,000 TPM limit.
        6,000 tokens ~= 24,000 characters. 
        We use 15,000 chars to leave a very safe buffer for system prompts and output.
        """
        if len(text) <= max_chars:
            return text
        
        logger.info(f"Truncating text from {len(text)} to {max_chars} chars for 8B model agents.")
        return text[:max_chars] + "\n...[Text truncated due to API rate limits]..."

    def run_analysis(
        self,
        file_id: str = None,
        text: str = None,
        images: list = None,
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
        # NEW STEP: Paper Discovery & Knowledge Base Update
        # ---------------------------------------------------------
        if file_id:
            try:
                # Construct path to the uploaded PDF file
                uploads_dir = os.path.join(self.settings.STORAGE_ROOT, self.settings.UPLOADS_DIR)
                pdf_path = os.path.join(uploads_dir, f"{file_id}.pdf")
                
                if os.path.exists(pdf_path):
                    logger.info(f"Running Paper Discovery Service for {file_id}...")
                    discovery_service = PaperDiscoveryService()
                    # This will find similar papers and save them to Parquet
                    discovery_service.find_similar_papers(pdf_path)
                else:
                    logger.warning(f"PDF file not found at {pdf_path}, skipping discovery step.")
            except Exception as e:
                # We catch exceptions here so discovery failure doesn't stop the main analysis
                logger.error(f"Paper Discovery failed (continuing with analysis): {e}")

        # ---------------------------------------------------------
        # Agent Analysis Pipeline
        # ---------------------------------------------------------
        
        # 2. Prepare Text Versions
        # Proofreader uses 70B model (higher limits), gets FULL text.
        full_text = text
        
        # Structure, Citation, Plagiarism use 8B model (strict 6k TPM limit), get TRUNCATED text.
        safe_text_8b = self._truncate_text_for_8b_model(full_text)

        # 3. Create Agents
        proof = create_proofreader()
        struct = create_structure_agent()
        consist = create_consistency_agent()
        cite = create_citation_agent() if enable_citation else None
        plag = create_plagiarism_agent() if enable_plagiarism else None

        # 4. Create Tasks
        # Note: We pass the safe_text_8b to agents liable to hit the 6k limit
        tasks = [
            create_proofreading_task(proof, full_text),       # 70B Model (Safe for large context)
            create_structure_task(struct, safe_text_8b),      # 8B Model (Needs truncation)
            create_consistency_task(consist, safe_text_8b),   # Qwen Model (Safe to truncate)
        ]

        if cite:
            tasks.append(create_citation_task(cite, safe_text_8b)) # 8B Model

        if plag:
            tasks.append(create_plagiarism_task(plag, safe_text_8b)) # 8B Model

        # 5. Gather Active Agents
        agents = [a for a in [proof, struct, cite, consist, plag] if a is not None]

        # 6. Run Main Crew
        crew = Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
            memory=False,
            embedder={
                "provider": "huggingface",
                "config": {"model": self.settings.EMBEDDING_MODEL_NAME},
            },
        )

        logger.info("Running main analysis crew...")
        result = crew.kickoff()

        # 7. Parse Results
        structured_results = {}
        
        try:
            if hasattr(crew, "tasks") and crew.tasks:
                for task in crew.tasks:
                    if hasattr(task, "output") and task.output:
                        output_value = str(task.output)
                        desc = task.description.lower()
                        if "proofreading" in desc:
                            structured_results["proofreading"] = output_value
                        elif "structure" in desc:
                            structured_results["structure"] = output_value
                        elif "citation" in desc:
                            structured_results["citations"] = output_value
                        elif "consistency" in desc:
                            structured_results["consistency"] = output_value
                        elif "plagiarism" in desc:
                            structured_results["plagiarism"] = output_value
        except Exception as e:
            logger.debug(f"Could not extract individual task outputs: {e}")

        if not structured_results:
            structured_results["raw"] = str(result)

        # 8. Run Vision Analysis (Separate Crew)
        if enable_vision and images:
            logger.info("Running vision analysis on extracted images...")
            vision = create_vision_agent()
            vision_task = create_vision_task(vision, images)

            vision_crew = Crew(
                agents=[vision],
                tasks=[vision_task],
                process=Process.sequential,
                verbose=True,
                memory=False,
            )

            try:
                vision_result = vision_crew.kickoff()
                structured_results["vision"] = str(vision_result)
            except Exception as e:
                logger.warning(f"Vision analysis failed: {e}")
                structured_results["vision"] = None
        else:
            structured_results["vision"] = None

        logger.info("Analysis complete")
        return structured_results

# Wrapper function to maintain backward compatibility with run_analysis.py
def run_full_analysis(
    file_id: str = None,
    text: str = None,
    images: list = None,
    enable_plagiarism: bool = True,
    enable_vision: bool = True,
    enable_citation: bool = True,
):
    service = AnalysisOrchestratorService()
    return service.run_analysis(
        file_id=file_id,
        text=text,
        images=images,
        enable_plagiarism=enable_plagiarism,
        enable_vision=enable_vision,
        enable_citation=enable_citation
    )