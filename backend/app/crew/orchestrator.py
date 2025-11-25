import json
from typing import Optional

from crewai import Crew, Process

from app.config import get_settings
from app.crew.agents.proofreader_agent import create_proofreader
from app.crew.agents.structure_agent import create_structure_agent
from app.crew.agents.citation_agent import create_citation_agent
from app.crew.agents.consistency_agent import create_consistency_agent
from app.crew.agents.vision_agent import create_vision_agent
from app.crew.agents.plagiarism_agent import create_plagiarism_agent
from app.crew.agents.compression_agent import create_compression_agent

from app.crew.tasks.proofreading_task import create_proofreading_task
from app.crew.tasks.structure_task import create_structure_task
from app.crew.tasks.citation_task import create_citation_task
from app.crew.tasks.consistency_task import create_consistency_task
from app.crew.tasks.vision_task import create_vision_task
from app.crew.tasks.plagiarism_task import create_plagiarism_task
from app.crew.tasks.compression_task import create_compression_task

from app.services.chunker import chunk_text
from app.crew.tools.pdf_tool import load_pdf
from app.services.token_budget import get_token_tracker
from app.utils.logging import logger

settings = get_settings()


def run_full_analysis(
    file_id: str,
    enable_plagiarism: bool = True,
    enable_vision: bool = True,
    enable_citation: bool = True,
    max_chunks_to_compress: Optional[int] = None,  # Use config default if None
):
    pdf_data = load_pdf(file_id)

    text = pdf_data["text"]
    images = pdf_data["images"]

    # Use configured limits if not explicitly provided
    if max_chunks_to_compress is None:
        max_chunks_to_compress = settings.MAX_CHUNKS_TO_COMPRESS
    max_text_length = settings.MAX_ANALYSIS_TEXT_LENGTH
    
    # OPTIMIZATION: Limit chunks to compress (avoid excessive token usage)
    chunks = chunk_text(text)
    chunks_to_process = chunks[:max_chunks_to_compress]
    
    if len(chunks) > max_chunks_to_compress:
        logger.info(f"Compressing only first {max_chunks_to_compress}/{len(chunks)} chunks to reduce token usage")
        # For any remaining chunks beyond the limit, include them as-is (uncompressed)
        remaining_text = "\n\n".join(chunks[max_chunks_to_compress:])
    else:
        remaining_text = ""

    compression_agent = create_compression_agent()
    compression_tasks = [
        create_compression_task(compression_agent, c) for c in chunks_to_process
    ]

    compression_crew = Crew(
        agents=[compression_agent],
        tasks=compression_tasks,
        verbose=False
    )

    try:
        compressed_results = compression_crew.kickoff()
        compressed_text = "\n\n".join(compressed_results)
    except Exception as e:
        logger.warning(f"Compression failed ({e}), using original text chunks instead")
        compressed_text = "\n\n".join(chunks_to_process)
    
    # OPTIMIZATION: Append any un-compressed chunks
    if remaining_text:
        compressed_text = compressed_text + "\n\n[Additional sections below]\n\n" + remaining_text

    # OPTIMIZATION: Truncate final text to avoid excessive token usage in downstream tasks
    if len(compressed_text) > max_text_length:
        compressed_text = compressed_text[:max_text_length] + "\n\n[... text truncated for token efficiency ...]"
        logger.info(f"Truncated analysis text to {max_text_length} chars for token efficiency")

    # STEP 2 — Send COMPRESSED TEXT to main analysis agents (excluding vision, which runs separately)
    proof = create_proofreader()
    struct = create_structure_agent()
    cite = create_citation_agent() if enable_citation else None
    consist = create_consistency_agent()
    plag = create_plagiarism_agent() if enable_plagiarism else None

    tasks = [
        create_proofreading_task(proof, compressed_text),
        create_structure_task(struct, compressed_text),
        create_consistency_task(consist, compressed_text),
    ]

    if cite:
        tasks.append(create_citation_task(cite, compressed_text))

    if plag:
        tasks.append(create_plagiarism_task(plag, compressed_text))

    agents = [
        a for a in [proof, struct, cite, consist, plag]
        if a is not None
    ]

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
    
    # OPTIMIZATION: Run vision task separately to avoid message length limits
    # Vision tasks don't need context from other tasks, only image paths
    vision_result = None
    if enable_vision and images:
        logger.info("Running vision analysis separately...")
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
        except Exception as e:
            logger.warning(f"Vision analysis failed: {e}")
            vision_result = None

    # Log token usage for monitoring
    tracker = get_token_tracker()
    logger.info(f"Analysis complete. Estimated tokens used: {tracker.tokens_used}/{tracker.safety_threshold}")

    try:
        # Merge vision results if available
        if isinstance(result, str):
            result_dict = json.loads(result)
        else:
            result_dict = result if isinstance(result, dict) else {"raw": str(result)}
        
        if vision_result:
            result_dict["vision_analysis"] = vision_result
        
        return result_dict
    except Exception:
        return {"raw": str(result), "vision_analysis": vision_result if vision_result else None}
