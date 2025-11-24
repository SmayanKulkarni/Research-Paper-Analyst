import json

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
from app.utils.logging import logger

settings = get_settings()


def run_full_analysis(
    file_id: str,
    enable_plagiarism: bool = True,
    enable_vision: bool = True,
):
    pdf_data = load_pdf(file_id)
    text = pdf_data["text"]
    images = pdf_data["images"]

    # Agents
    proof = create_proofreader()
    struct = create_structure_agent()
    cite = create_citation_agent()
    consist = create_consistency_agent()
    vision = create_vision_agent() if (enable_vision and images) else None
    plag = create_plagiarism_agent() if enable_plagiarism else None

    # Tasks
    tasks = [
        create_proofreading_task(proof, text),
        create_structure_task(struct, text),
        create_citation_task(cite, text),
        create_consistency_task(consist, text),
    ]

    if vision:
        tasks.append(create_vision_task(vision, images))

    if plag:
        tasks.append(create_plagiarism_task(plag, text))

    agents = [a for a in [proof, struct, cite, consist, vision, plag] if a is not None]

    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        memory=False,
        embedder={
            "provider": "huggingface",
            "config": {
                "model": settings.EMBEDDING_MODEL_NAME,
            },
        },
    )

    logger.info("Starting crew analysis pipeline...")
    result = crew.kickoff()

    # CrewAI may return a string or already a JSON-like object.
    try:
        if isinstance(result, str):
            return json.loads(result)
        return result
    except Exception:
        return {"raw": str(result)}
