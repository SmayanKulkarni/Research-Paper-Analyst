from crewai import Agent

from app.config import get_settings

settings = get_settings()
GROQ_MODEL = settings.GROQ_MODEL_NAME


def create_citation_agent() -> Agent:
    return Agent(
        role="Citation and Referencing Specialist",
        goal=(
            "Identify missing citations, incorrect referencing, and uncredited claims "
            "in research manuscripts."
        ),
        backstory=(
            "You are meticulous about academic honesty, familiar with common "
            "citation styles and best practices for attribution."
        ),
        llm=GROQ_MODEL,
        verbose=True,
        allow_delegation=False,
    )
