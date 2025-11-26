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

from app.crew.tasks.proofreading_task import create_proofreading_task
from app.crew.tasks.structure_task import create_structure_task
from app.crew.tasks.citation_task import create_citation_task
from app.crew.tasks.consistency_task import create_consistency_task
from app.crew.tasks.vision_task import create_vision_task
from app.crew.tasks.plagiarism_task import create_plagiarism_task

from app.services.chunker import chunk_text
from app.crew.tools.pdf_tool import load_pdf
from app.services.token_budget import get_token_tracker
from app.services.token_counter import log_token_summary, create_token_summary
from app.services.nlp_preprocessor import preprocess_research_paper, preprocess_for_chunk_compression
from app.services.compression import batch_compress_chunks
from app.utils.logging import logger

settings = get_settings()


def run_full_analysis(
    file_id: str,
    enable_plagiarism: bool = True,
    enable_vision: bool = True,
    enable_citation: bool = True,
    enable_nlp_preprocessing: bool = False,  # DISABLED by default due to TPM limits
    max_chunks_to_compress: Optional[int] = None,  # Use config default if None
):
    pdf_data = load_pdf(file_id)

    text = pdf_data["text"]
    images = pdf_data["images"]

    # Use configured limits if not explicitly provided
    if max_chunks_to_compress is None:
        max_chunks_to_compress = settings.MAX_CHUNKS_TO_COMPRESS
    max_text_length = settings.MAX_ANALYSIS_TEXT_LENGTH
    
    # OPTIMIZATION STEP 1: Apply NLP preprocessing BEFORE chunking (DISABLED by default)
    # This extracts summaries, key phrases, and entities to reduce token usage
    # Note: Re-enable only when TPM limits allow
    if enable_nlp_preprocessing:
        logger.info("Applying NLP preprocessing to research paper...")
        try:
            preprocess_result = preprocess_research_paper(
                text,
                enable_summarization=True,
                enable_key_phrases=True,
                enable_entities=False,  # Disable for speed
                max_output_length=5000,
            )
            preprocessed_text = preprocess_result["processed_text"]
            token_savings = preprocess_result["token_savings_estimate"]
            logger.info(f"NLP preprocessing complete. Estimated token savings: ~{token_savings} tokens")
            
            # Log token summary for monitoring
            token_summary = create_token_summary(text)
            logger.info(f"Original text: {token_summary['input_tokens_simple']} tokens")
            token_summary_after = create_token_summary(preprocessed_text)
            logger.info(f"After NLP preprocessing: {token_summary_after['input_tokens_simple']} tokens")
        except Exception as e:
            logger.warning(f"NLP preprocessing failed ({e}), using original text")
            preprocessed_text = text
    else:
        preprocessed_text = text
        logger.info("NLP preprocessing disabled (enable_nlp_preprocessing=False)")
    
    # OPTIMIZATION STEP 2: Use extractive summarization to compress chunks (NO LLM)
    chunks = chunk_text(preprocessed_text)
    chunks_to_process = chunks[:max_chunks_to_compress]
    
    if len(chunks) > max_chunks_to_compress:
        logger.info(f"Compressing only first {max_chunks_to_compress}/{len(chunks)} chunks to reduce token usage")
        # For any remaining chunks beyond the limit, include them as-is (uncompressed)
        remaining_text = "\n\n".join(chunks[max_chunks_to_compress:])
    else:
        remaining_text = ""

    # Use non-LLM extractive summarization for compression
    try:
        logger.info(f"Applying extractive summarization to {len(chunks_to_process)} chunks...")
        compressed_chunks = batch_compress_chunks(chunks_to_process, compression_ratio=0.5)
        compressed_text = "\n\n".join(compressed_chunks)
        logger.info(f"Compression complete. Result: {len(compressed_text)} chars")
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

    # Log token usage for this intermediate step
    log_token_summary(compressed_text, context="post-compression")

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
    
    # Parse CrewAI task outputs into structured results
    # CrewAI returns a TaskOutput object or string; we need to extract individual task outputs
    structured_results = {}
    
    try:
        # Try to get individual task outputs from the crew
        # Each task has an output that we can map to analysis categories
        if hasattr(crew, "tasks") and crew.tasks:
            for task in crew.tasks:
                if hasattr(task, "output") and task.output:
                    output_value = str(task.output)
                    if "proofreading" in task.description.lower():
                        structured_results["proofreading"] = output_value
                    elif "structure" in task.description.lower():
                        structured_results["structure"] = output_value
                    elif "citation" in task.description.lower():
                        structured_results["citations"] = output_value
                    elif "consistency" in task.description.lower():
                        structured_results["consistency"] = output_value
                    elif "plagiarism" in task.description.lower():
                        structured_results["plagiarism"] = output_value
    except Exception as e:
        logger.debug(f"Could not extract individual task outputs: {e}")
    
    # If we couldn't parse individual outputs, treat the whole result as one output
    if not structured_results:
        structured_results["raw"] = str(result)
    
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
            structured_results["vision"] = str(vision_result)
        except Exception as e:
            logger.warning(f"Vision analysis failed: {e}")
            structured_results["vision"] = None

    # Log token usage for monitoring
    tracker = get_token_tracker()
    logger.info(f"Analysis complete. Estimated tokens used: {tracker.tokens_used}/{tracker.safety_threshold}")

    return structured_results
