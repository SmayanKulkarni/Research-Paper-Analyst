from crewai import Agent

from app.config import get_settings

settings = get_settings()
GROQ_MODEL = settings.GROQ_MODEL_NAME


def create_proofreader() -> Agent:
    return Agent(
        role="Academic Proofreader",
        goal=(
            "Improve clarity, grammar, coherence, and academic tone in research papers "
            "while preserving the original meaning."
        ),
        backstory=(
            "You are an expert academic editor with years of experience refining "
            "conference and journal submissions across computer science and engineering."
        ),
        llm=GROQ_MODEL,
        verbose=True,
        allow_delegation=False,
    )
