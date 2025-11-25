from crewai import Agent
from app.services.llm_provider import get_crewai_llm


# Proofreader is a heavier task; limit per-call completion size and prefer fewer concurrent calls
llm = get_crewai_llm(temperature=0.25, max_tokens=256)


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
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )