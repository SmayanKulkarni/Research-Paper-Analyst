from crewai import Agent

from app.config import get_settings

settings = get_settings()
GROQ_MODEL = settings.GROQ_MODEL_NAME


def create_consistency_agent() -> Agent:
    return Agent(
        role="Consistency and Coherence Checker",
        goal=(
            "Detect contradictions, inconsistent terminology, and mismatched references "
            "across the research paper."
        ),
        backstory=(
            "You specialize in reading entire manuscripts end-to-end to ensure that "
            "definitions, symbols, and claims stay consistent."
        ),
        llm=GROQ_MODEL,
        verbose=True,
        allow_delegation=False,
    )
