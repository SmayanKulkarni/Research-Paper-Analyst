from crewai import Agent
from app.services.llm_provider import get_crewai_llm
from app.config import get_settings


def create_structure_agent(max_tokens: int = None) -> Agent:
    """
    Create a Structure Analysis Agent.
    
    This agent analyzes document organization, section flow, and logical structure.
    
    Args:
        max_tokens: Dynamic token limit based on paper length
    
    Returns:
        CrewAI Agent for structure analysis
    """
    settings = get_settings()
    
    if max_tokens is None:
        max_tokens = settings.MAX_COMPLETION_TOKENS
    
    llm = get_crewai_llm(
        model=settings.CREW_STRUCTURE_MODEL,
        temperature=0.2,
        max_tokens=max_tokens,
    )
    
    return Agent(
        role="Research Structure Analyst",
        goal=(
            "Quickly evaluate paper structure from section headings. "
            "Identify missing sections and provide 3-5 recommendations. Finish in one pass."
        ),
        backstory=(
            "You are an efficient academic reviewer. You assess structure quickly "
            "and provide concise, actionable feedback."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=1,  # Single pass
        max_retry_limit=0,  # No retries
    )
