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
            "Analyze the scientific FIGURES from a research paper.\n\n"
            "IMAGE PATHS TO ANALYZE:\n"
            f"{image_paths_str}\n\n"
            "INSTRUCTIONS:\n"
            "1. Use the 'Analyze Scientific Images' tool with the image paths above\n"
            "2. For EACH figure, assess:\n"
            "   - Figure type (chart, diagram, table, photo, etc.)\n"
            "   - Clarity and readability\n"
            "   - Label completeness (axis labels, legends, captions)\n"
            "   - Data presentation quality\n"
            "3. Provide overall assessment of figure quality\n"
            "4. List specific improvements for each figure\n\n"
            "DO NOT analyze any text - focus ONLY on the visual elements."
        ),
        expected_output=(
            "A figure quality report containing:\n"
            "- Individual analysis for each figure\n"
            "- Overall quality score\n"
            "- Specific recommendations for improvement"
        ),
        agent=agent,
        # No context from other tasks - vision analysis is completely independent
        context=None,
    )
