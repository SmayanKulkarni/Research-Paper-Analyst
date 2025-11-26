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

# backend/app/crew/orchestrator.py
from crewai import Crew, Process
from app.config import get_settings
# ... [Keep all your imports] ...
from app.crew.tools.pdf_tool import load_pdf
from app.utils.logging import logger

settings = get_settings()

def run_full_analysis(
    file_id: str = None,           # Made optional
    text: str = None,              # Added argument
    images: list = None,           # Added argument
    enable_plagiarism: bool = True,
    enable_vision: bool = True,
    enable_citation: bool = True,
):
    """
    Run full multi-agent paper analysis pipeline.
    
    Args:
        file_id: UUID of uploaded PDF file (optional if text is provided)
        text: Full text of the paper (optional, overrides file_id)
        images: List of image paths (optional)
        enable_plagiarism: Run plagiarism check
        enable_vision: Run vision analysis (requires images)
        enable_citation: Run citation analysis
    """
    
    # Handle input source: either file_id or direct text
    if text is None:
        if file_id is None:
            raise ValueError("Either file_id or text must be provided")
        pdf_data = load_pdf(file_id)
        text = pdf_data["text"]
        images = pdf_data["images"]
    else:
        # Default images to empty list if not provided
        if images is None:
            images = []

    log_label = file_id if file_id else "direct_input"
    logger.info(f"Starting crew analysis for {log_label}")

    # Create all agents
    proof = create_proofreader()
    struct = create_structure_agent()
    consist = create_consistency_agent()
    cite = create_citation_agent() if enable_citation else None
    plag = create_plagiarism_agent() if enable_plagiarism else None

    # Build task list (core tasks)
    tasks = [
        create_proofreading_task(proof, text),
        create_structure_task(struct, text),
        create_consistency_task(consist, text),
    ]

    if cite:
        tasks.append(create_citation_task(cite, text))

    if plag:
        tasks.append(create_plagiarism_task(plag, text))

    # Gather active agents
    agents = [a for a in [proof, struct, cite, consist, plag] if a is not None]

    # Run main crew analysis
    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        memory=False,
        embedder={
            "provider": "huggingface",
            "config": {"model": settings.EMBEDDING_MODEL_NAME},
        },
    )

    logger.info("Running main analysis crew...")
    result = crew.kickoff()

    # Parse structured results
    structured_results = {}

    # Extract outputs safely
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

    # Run vision analysis separately if enabled and images exist
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