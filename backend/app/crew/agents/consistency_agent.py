from crewai import Agent
from app.services.llm_provider import get_crewai_llm


# Consistency checks are mid-weight; reduce max_tokens to save TPM
llm = get_crewai_llm(temperature=0.2, max_tokens=128)


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
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )