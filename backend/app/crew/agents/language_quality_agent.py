"""
Language Quality Agent - Comprehensive agent for grammar, clarity, tone, and consistency.

This agent combines the responsibilities of the former Proofreader and Consistency agents
to provide a thorough, holistic language analysis.
"""

from crewai import Agent
from app.services.llm_provider import get_crewai_llm
from app.config import get_settings


def create_language_quality_agent(max_tokens: int = None) -> Agent:
    """
    Create a comprehensive Language Quality Agent.
    
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
            "Perform a THOROUGH analysis of the research paper's language quality. "
            "Identify ALL grammar errors, clarity issues, style problems, and inconsistencies. "
            "Accuracy and completeness are the priority - take your time to be thorough."
        ),
        backstory=(
            "You are a meticulous academic editor with decades of experience reviewing "
            "research papers across multiple disciplines. You have an eagle eye for "
            "grammatical errors, awkward phrasing, inconsistent terminology, and style issues. "
            "You believe every paper deserves a thorough review to help authors produce "
            "their best work. You don't rush - you methodically analyze each section."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=3,  # Allow multiple passes for thorough analysis
        max_retry_limit=1,  # One retry on failure
    )
