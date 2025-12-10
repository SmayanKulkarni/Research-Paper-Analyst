"""
Plagiarism Agent - Detects potential content overlap using Semantic Scholar.
Uses free Semantic Scholar API to find similar papers, then analyzes overlap.
"""

from crewai import Agent
from app.services.llm_provider import get_crewai_llm
from app.config import get_settings
from app.crew.tools.semantic_scholar_tool import search_similar_papers


def create_plagiarism_agent(max_tokens: int = None) -> Agent:
    """
    Create a Plagiarism Detection Agent.
    
    This agent uses Semantic Scholar to find similar papers and
    analyzes potential content overlap or missing citations.
    
    Args:
        max_tokens: Dynamic token limit based on paper length
    
    Returns:
        CrewAI Agent for plagiarism detection
    """
    settings = get_settings()
    
    if max_tokens is None:
        max_tokens = settings.MAX_COMPLETION_TOKENS
    
    llm = get_crewai_llm(
        model=settings.CREW_PLAGIARISM_MODEL,
        temperature=0.1,
        max_tokens=max_tokens,
    )
    
    return Agent(
        role="Plagiarism and Originality Checker",
        goal=(
            "Search for similar papers in academic databases and analyze potential "
            "content overlap. Identify if the paper properly cites prior work or "
            "if there are concerning similarities that need addressing."
        ),
        backstory=(
            "You are an experienced academic integrity officer who specializes in "
            "detecting potential plagiarism and ensuring proper attribution. You use "
            "Semantic Scholar to find related papers and carefully analyze whether "
            "the work is original or if it borrows too heavily from existing literature. "
            "You understand that similar ideas in the same field are normal, but "
            "identical phrasing or uncited borrowed concepts are problematic."
        ),
        llm=llm,
        tools=[search_similar_papers],
        verbose=True,
        allow_delegation=False,
        max_iter=3,
        max_retry_limit=1,
    )
