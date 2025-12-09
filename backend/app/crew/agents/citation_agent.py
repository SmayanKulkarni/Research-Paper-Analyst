"""
Citation Agent - Checks citation-reference consistency within a paper.
No external API calls - purely internal analysis.
"""

from crewai import Agent
from app.services.llm_provider import get_crewai_llm
from app.config import get_settings
from app.crew.tools.citation_tool import check_citation_references


def create_citation_agent(max_tokens: int = None) -> Agent:
    """
    Create a Citation Reference Consistency Agent.
    
    This agent checks if all citations in the paper are properly referenced
    and all references are actually cited in the content.
    
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
        role="Citation Reference Consistency Checker",
        goal=(
            "Check if all citations in the paper content (like [1], [2], etc.) have "
            "corresponding entries in the References section, and if all references "
            "are actually cited in the paper. Identify any mismatches or gaps."
        ),
        backstory=(
            "You are a meticulous academic editor who specializes in verifying that "
            "papers have consistent citation-reference linking. You check that every "
            "numbered citation in the text has a matching reference, and every reference "
            "in the bibliography is actually used in the paper."
        ),
        llm=llm,
        tools=[check_citation_references],
        verbose=True,
        allow_delegation=False,
        max_iter=2,
        max_retry_limit=1,
    )
