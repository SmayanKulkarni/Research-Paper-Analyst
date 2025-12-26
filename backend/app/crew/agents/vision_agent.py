from crewai import Agent
from app.crew.tools.vision_tool import vision_tool
from app.services.llm_provider import get_crewai_vision_llm
from app.config import get_settings


def create_vision_agent():
    settings = get_settings()
    # Vision agent uses its dedicated vision model
    llm = get_crewai_vision_llm(model=settings.CREW_VISION_MODEL, temperature=0.1)
    
    return Agent(
        role="Scientific Image Reviewer",
        backstory=(
            "You call the image analysis tool with image paths. "
            "You report the tool's output exactly as provided, without modification or additional commentary. "
            "Some images may fail analysis due to being corrupted, blank, or extracted artifacts - report those failures honestly."
        ),
        goal=(
            "Call the 'Analyze Scientific Images' tool with the provided image paths. "
            "Return the tool's output exactly as provided. Do not add internal thoughts, reasoning, or final answer sections. "
            "If the tool reports failures or errors, include those in the output as-is."
        ),
        llm=llm,
        tools=[vision_tool],
        verbose=False,
        max_iter=1,  # Single iteration: call tool, return result
        max_retry_limit=0,  # No retries
    )