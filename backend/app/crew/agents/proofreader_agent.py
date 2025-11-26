from crewai import Agent
from app.services.llm_provider import get_crewai_llm
from app.config import get_settings


def create_proofreader() -> Agent:
    settings = get_settings()
    # Proofreader uses openai/gpt-oss-120b (most powerful, best for language tasks)
    llm = get_crewai_llm(model=settings.CREW_PROOFREADER_MODEL, temperature=0.25, max_tokens=512)
    
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