from crewai import Agent
from app.services.llm_provider import get_crewai_llm
from app.config import get_settings
from app.crew.tools.citation_tool import verify_citation_integrity


def create_citation_agent(max_tokens: int = None) -> Agent:
    """
    Create a comprehensive Citation Verification Agent.
    
    This agent verifies citation integrity using the citation verification tool
    and performs thorough analysis of all references in the paper.
    
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
        role="Citation and Reference Integrity Specialist",
        goal=(
            "Perform a COMPREHENSIVE citation analysis. Verify the most critical citations "
            "using the verification tool (up to 10 citations). Analyze reference formatting, "
            "identify missing citations, and assess overall citation quality. "
            "If a citation cannot be verified, mark it as 'unverified' and continue."
        ),
        backstory=(
            "You are an expert academic auditor and bibliometrics specialist with deep "
            "knowledge of citation standards across multiple disciplines. You understand "
            "the importance of accurate citations for academic integrity and can quickly "
            "identify problematic references, missing citations, and format inconsistencies. "
            "You provide thorough analysis while being practical about verification limitations."
        ),
        llm=llm,
        tools=[verify_citation_integrity],
        verbose=True,
        allow_delegation=False,
        max_iter=5,  # Allow more iterations for thorough citation checks
        max_retry_limit=1,  # One retry on failure
    )
