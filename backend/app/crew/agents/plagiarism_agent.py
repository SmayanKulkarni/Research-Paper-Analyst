from crewai import Agent
from app.crew.tools.plagiarism_tool import plagiarism_tool
from app.services.llm_provider import get_crewai_llm
from app.config import get_settings


def create_plagiarism_agent(max_tokens: int = None) -> Agent:
    """
    Create a Plagiarism Detection Agent.
    
    This agent uses the plagiarism tool to check for similar content.
    
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
        role="Plagiarism and Similarity Analyst",
        goal=(
            "Run the plagiarism tool ONCE on the paper text and report results. "
            "Do NOT retry if the tool fails - report the failure and finish."
        ),
        backstory=(
            "You are an academic integrity officer. You run the plagiarism check once "
            "and report findings. You never retry failed checks."
        ),
        llm=llm,
        tools=[plagiarism_tool],
        verbose=True,
        allow_delegation=False,
        max_iter=1,  # Single iteration only
        max_retry_limit=0,  # Disable retries completely
    )
