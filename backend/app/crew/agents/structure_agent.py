from crewai import Agent
from app.services.llm_provider import get_crewai_llm


# Structure analysis can be concise; reduce max_tokens
llm = get_crewai_llm(temperature=0.2, max_tokens=128)


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
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )