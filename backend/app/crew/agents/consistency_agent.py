from crewai import Agent
from app.services.llm_provider import get_crewai_llm
from app.config import get_settings


def create_consistency_agent() -> Agent:
    settings = get_settings()
    # Consistency agent uses qwen/qwen3-32b (powerful for detailed analysis)
    llm = get_crewai_llm(model=settings.CREW_CONSISTENCY_MODEL, temperature=0.2, max_tokens=1000)
    
    return Agent(
        role="Consistency and Coherence Checker",
        goal=(
            "Detect contradictions, inconsistent terminology, and mismatched references "
            "across the research paper."
            'The inconsistencies can be any and all types of small mistakes, numerical and logical fallacies and so on.'
        ),
        backstory=(
            "You specialize in reading entire manuscripts end-to-end to ensure that "
            "definitions, symbols, and claims stay consistent."
            "You are strict in your observations and less forgiving."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )