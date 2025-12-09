from crewai import Agent
from app.crew.tools.plagiarism_tool import plagiarism_tool
from app.services.llm_provider import get_crewai_llm
from app.config import get_settings


def create_plagiarism_agent(max_tokens: int = None) -> Agent:
    """
    Create a comprehensive Plagiarism Detection Agent.
    
    This agent uses the plagiarism tool (which combines vector similarity
    and web search) to check for similar content and provide detailed analysis.
    
    Args:
        max_tokens: Dynamic token limit based on paper length
    
    Returns:
        CrewAI Agent for plagiarism analysis
    """
    settings = get_settings()
    
    if max_tokens is None:
        max_tokens = settings.MAX_COMPLETION_TOKENS
    
    llm = get_crewai_llm(
        model=settings.CREW_PLAGIARISM_MODEL,
        temperature=0.3,
        max_tokens=max_tokens,
    )
    
    return Agent(
        role="Academic Integrity & Plagiarism Specialist",
        goal=(
            "Perform a COMPREHENSIVE plagiarism and originality check using the plagiarism tool. "
            "Analyze the results thoroughly and provide a detailed report on the paper's originality. "
            "Distinguish between legitimate citations/quotes and potential plagiarism."
        ),
        backstory=(
            "You are a senior academic integrity officer with expertise in plagiarism detection "
            "and originality assessment. You understand that not all similarity is plagiarism - "
            "proper citations, common terminology, and quoted material are expected. You can "
            "distinguish between concerning similarity and acceptable matches. You provide "
            "nuanced analysis that helps authors understand and address any issues."
        ),
        llm=llm,
        tools=[plagiarism_tool],
        verbose=True,
        allow_delegation=False,
        max_iter=3,  # Allow thorough analysis of results
        max_retry_limit=1,  # One retry if tool fails
    )
