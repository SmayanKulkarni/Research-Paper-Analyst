from crewai import Agent
from app.services.llm_provider import get_crewai_llm
from app.config import get_settings


def create_structure_agent() -> Agent:
    settings = get_settings()
    # Structure agent uses openai/gpt-oss-20b (good balance of capability and cost)
    llm = get_crewai_llm(model=settings.CREW_STRUCTURE_MODEL, temperature=0.2, max_tokens=1000)
    
    return Agent(
        role="Research Structure Analyst",
        goal=(
            "Evaluate and improve the overall structure, section flow, and organization "
            "of research papers."
        ),
        backstory=(
            "You are a senior reviewer who focuses on whether papers are logically "
            "organized, with clear sections, contributions, and conclusions."
            "You are strict in your observations and less forgiving."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )