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
    def __init__(self):
        self.settings = get_settings()
        
    def run_analysis(
        self,
        file_id: str = None,
        text: str = None,
        images: list = None,
        enable_plagiarism: bool = True,
        enable_vision: bool = True,
        enable_citation: bool = True,
    ) -> Dict[str, Any]:
        
        # 1. Load Data
        if text is None:
            if file_id is None: raise ValueError("No input provided")
            pdf_data = load_pdf(file_id)
            text = pdf_data["text"]
            images = pdf_data["images"]
        else:
            if images is None: images = []

        # Ensure text is string
        if not text: text = ""

        # 2. Discovery & Indexing
        if file_id:
            try:
                uploads_dir = os.path.join(self.settings.STORAGE_ROOT, self.settings.UPLOADS_DIR)
                pdf_path = os.path.join(uploads_dir, f"{file_id}.pdf")
                if os.path.exists(pdf_path):
                    logger.info("Running Paper Discovery (Indexing to FAISS)...")
                    PaperDiscoveryService().find_similar_papers(pdf_path)
            except Exception as e:
                logger.error(f"Discovery failed: {e}")

        # 3. Prepare Text
        full_text = text
        logger.info(f"Processing full text: {len(full_text)} characters.")

        # 4. Init Agents
        proof = create_proofreader()
        struct = create_structure_agent()
        consist = create_consistency_agent()
        cite = create_citation_agent() if enable_citation else None
        plag = create_plagiarism_agent() if enable_plagiarism else None

        # 5. Create Tasks
        tasks = [
            create_proofreading_task(proof, full_text),
            create_structure_task(struct, full_text),
            create_consistency_task(consist, full_text),
        ]
        if cite: tasks.append(create_citation_task(cite, full_text))
        if plag: tasks.append(create_plagiarism_task(plag, full_text))

        # 6. Execute
        agents = [a for a in [proof, struct, cite, consist, plag] if a is not None]
        crew = Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
            memory=False,
            embedder={"provider": "huggingface", "config": {"model": self.settings.EMBEDDING_MODEL_NAME}},
        )

        logger.info("Running Analysis Crew...")
        result = crew.kickoff()
        
        # 7. Format Output
        structured_results = {}
        try:
            if hasattr(crew, "tasks"):
                for task in crew.tasks:
                    if task.output:
                        desc = task.description.lower()
                        output_str = str(task.output)
                        if "proofreading" in desc: structured_results["proofreading"] = output_str
                        elif "structure" in desc: structured_results["structure"] = output_str
                        elif "citation" in desc: structured_results["citations"] = output_str
                        elif "consistency" in desc: structured_results["consistency"] = output_str
                        elif "plagiarism" in desc: structured_results["plagiarism"] = output_str
        except Exception as e:
            logger.error(f"Error parsing task outputs: {e}")

        if not structured_results: structured_results["raw"] = str(result)

        # 8. Vision
        if enable_vision and images:
            try:
                vision_result = Crew(agents=[create_vision_agent()], tasks=[create_vision_task(create_vision_agent(), images)]).kickoff()
                structured_results["vision"] = str(vision_result)
            except: structured_results["vision"] = None
        else:
            structured_results["vision"] = None

        return structured_results

def run_full_analysis(**kwargs):
    return AnalysisOrchestratorService().run_analysis(**kwargs)