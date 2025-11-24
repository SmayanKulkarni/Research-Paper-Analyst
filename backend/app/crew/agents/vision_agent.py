from crewai import Agent
from app.config import get_settings
from app.crew.tools.vision_tool import vision_tool

settings = get_settings()


def create_vision_agent():
    return Agent(
        role="Scientific Image Reviewer",
        goal="Analyze figures using a vision model.",
        llm=settings.GROQ_VISION_MODEL_NAME,
        tools=[vision_tool],
        verbose=True
    )
    