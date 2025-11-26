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
            "You are skilled at interpreting scientific figures, charts, and diagrams "
            "to assess their clarity, accuracy, and relevance."
        ),
        goal="Analyze figures using a vision model. Be concise.",
        llm=llm,
        tools=[vision_tool],
        verbose=True,
        # OPTIMIZATION: Limit max iterations to reduce token usage
        max_iter=3,
    )