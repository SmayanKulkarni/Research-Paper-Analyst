from crewai import Agent
from app.services.llm_provider import get_crewai_llm
from app.config import get_settings
from app.crew.tools.citation_tool import verify_citation_integrity


def create_citation_agent(max_tokens: int = None) -> Agent:
    """
    Create a Citation Verification Agent.
    
    This agent verifies citation integrity using the citation verification tool.
    
    Args:
        max_tokens: Dynamic token limit based on paper length
    
    Returns:
        CrewAI Agent for citation analysis
    """
    settings = get_settings()
    
    if max_tokens is None:
        max_tokens = settings.MAX_COMPLETION_TOKENS
    
    llm = get_crewai_llm(
        model=settings.CREW_CITATION_MODEL,
        temperature=0.1,
        max_tokens=max_tokens,
    )
    
    return Agent(
        role="Citation and Referencing Specialist",
        goal=(
            "Verify 3-5 key citations for accuracy. Do NOT retry failed lookups - "
            "mark them as 'unverified' and move on. Be efficient."
        ),
        backstory=(
            "You are a meticulous academic auditor. When a citation cannot be verified, "
            "you note it as 'unverified' and continue. You never retry the same citation."
        ),
        llm=llm,
        tools=[verify_citation_integrity],
        verbose=True,
        allow_delegation=False,
        max_iter=2,  # Strict limit - no retries
        max_retry_limit=0,  # Disable retries completely
    )
