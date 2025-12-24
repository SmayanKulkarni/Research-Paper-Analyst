from crewai import Agent
from app.services.llm_provider import get_crewai_llm
from app.config import get_settings


def create_structure_agent(max_tokens: int = None) -> Agent:
    """
    Create a comprehensive Structure Analysis Agent.
    
    This agent analyzes document organization, section flow, logical structure,
    and adherence to academic paper conventions.
    
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
        role="Research Paper Structure Analyst",
        goal=(
            "Perform a THOROUGH structural analysis of the research paper. "
            "Evaluate organization, section completeness, logical flow, and adherence "
            "to academic conventions. Provide detailed, actionable recommendations. "
            "Formatting rules: Do NOT include internal thoughts, chain-of-thought, or meta commentary. "
            "Do NOT include headings like 'Thought', 'Reasoning', or 'Final Answer'. "
            "Return only the structured analysis."
        ),
        backstory=(
            "You are an experienced academic reviewer and journal editor who has "
            "evaluated thousands of research papers. You understand the nuances of "
            "paper structure across different fields and can identify when a paper's "
            "organization helps or hinders its impact. You provide comprehensive "
            "structural feedback that helps authors significantly improve their work."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=3,  # Allow thorough analysis
        max_retry_limit=1,  # One retry on failure
    )
