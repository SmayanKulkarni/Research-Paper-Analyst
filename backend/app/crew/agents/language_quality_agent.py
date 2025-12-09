"""
Language Quality Agent - Consolidated agent for grammar, clarity, tone, and consistency.

This agent combines the responsibilities of the former Proofreader and Consistency agents
to reduce the total number of agents and provide a more holistic language analysis.
"""

from crewai import Agent
from app.services.llm_provider import get_crewai_llm
from app.config import get_settings


def create_language_quality_agent(max_tokens: int = None) -> Agent:
    """
    Create a consolidated Language Quality Agent.
    
    This agent handles:
    - Grammar and spelling errors
    - Clarity and readability issues
    - Academic tone and style
    - Internal consistency (terminology, definitions, symbols)
    - Contradictions and mismatched references
    
    Args:
        max_tokens: Dynamic token limit based on paper length
    
    Returns:
        CrewAI Agent for language quality analysis
    """
    settings = get_settings()
    
    # Use the default completion tokens if not specified
    if max_tokens is None:
        max_tokens = settings.MAX_COMPLETION_TOKENS
    
    llm = get_crewai_llm(
        model=settings.CREW_PROOFREADER_MODEL,
        temperature=0.2,
        max_tokens=max_tokens,
    )
    
    return Agent(
        role="Academic Language & Consistency Specialist",
        goal=(
            "Quickly analyze the paper for top 5 language issues. "
            "Be concise and finish in one pass - no retries needed."
        ),
        backstory=(
            "You are an efficient academic editor. You scan papers quickly, "
            "identify the most important issues, and provide a concise report."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=1,  # Single pass analysis
        max_retry_limit=0,  # No retries
    )
