from crewai import Agent

from app.config import get_settings

settings = get_settings()
GROQ_MODEL = settings.GROQ_MODEL_NAME


def create_structure_agent() -> Agent:
    return Agent(
        role="Research Structure Analyst",
        goal=(
            "Evaluate and improve the overall structure, section flow, and organization "
            "of research papers."
        ),
        backstory=(
            "You are a senior reviewer who focuses on whether papers are logically "
            "organized, with clear sections, contributions, and conclusions."
        ),
        llm=GROQ_MODEL,
        verbose=True,
        allow_delegation=False,
    )
