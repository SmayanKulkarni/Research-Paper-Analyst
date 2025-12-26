from typing import List

from crewai import Task


def create_vision_task(agent, images: List[str]) -> Task:
    """
    Create a vision analysis task for scientific figures.
    
    IMPORTANT: This task receives ONLY image paths, NO paper text.
    The vision agent analyzes figures independently using the vision model.
    
    Args:
        agent: The vision agent (has vision tool access)
        images: List of image file paths to analyze
    
    Returns:
        CrewAI Task for vision analysis (images only, no text)
    """
    # Format image paths for the tool
    image_paths_str = ", ".join(images)
    
    return Task(
        description=(
            "Analyze the scientific FIGURES from a research paper using the vision tool.\n\n"
            "IMAGE PATHS TO ANALYZE:\n"
            f"{image_paths_str}\n\n"
            "INSTRUCTIONS:\n"
            "1. Call the 'Analyze Scientific Images' tool ONCE with the image paths above\n"
            "2. The tool will process each image independently\n"
            "3. Report the tool's output exactly as returned (do not modify or rewrite)\n"
            "4. If images are blank, corrupted, or unclear, the tool will report that\n"
            "5. If no images are available or all failed, report that clearly\n\n"
            "CRITICAL: Return ONLY the tool output. Do not add internal thoughts or meta commentary.\n\n"
            "Formatting Rules:\n"
            "- Include only the tool's output\n"
            "- Do NOT add internal thoughts, chain-of-thought, or meta commentary\n"
            "- Do NOT include 'Thought', 'Reasoning', or 'Final Answer' headings"
        ),
        expected_output=(
            "The exact output from the 'Analyze Scientific Images' tool, including per-image analysis "
            "with status (success or error), figure type, quality assessment, and recommendations. "
            "If any images failed, report that clearly."
        ),
        agent=agent,
        context=None,
    )
