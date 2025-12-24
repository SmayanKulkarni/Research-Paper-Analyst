"""
Flow Analysis Agent

Analyzes the narrative flow, transitions, and overall readability
of a research paper.
"""

from crewai import Agent
from app.services.llm_provider import get_crewai_llm
from app.config import get_settings


def create_flow_agent(max_tokens: int = None) -> Agent:
    """
    Create a Flow Analysis Agent.
    
    This agent evaluates:
    - Narrative flow and story arc
    - Quality of transitions between sections
    - Paragraph-level coherence
    - Reader experience and comprehension ease
    
    Args:
        max_tokens: Dynamic token limit based on paper length
    
    Returns:
        CrewAI Agent for flow analysis
    """
    settings = get_settings()
    
    if max_tokens is None:
        max_tokens = settings.MAX_COMPLETION_TOKENS
    
    llm = get_crewai_llm(
        model=settings.CREW_FLOW_MODEL,
        temperature=0.2,
        max_tokens=max_tokens,
    )
    
    return Agent(
        role="Narrative Flow & Readability Specialist",
        goal=(
            "Evaluate the paper's narrative flow, transitions, and overall readability. "
            "Identify where the paper loses momentum, has jarring transitions, or could "
            "guide the reader more smoothly through the content."
        ),
        backstory=(
            "You are an expert in scientific writing and narrative structure with a background "
            "in rhetoric and composition. You've taught academic writing for decades and have "
            "helped hundreds of researchers improve their manuscripts. You understand how to "
            "guide readers through complex ideas with smooth transitions, clear signposting, "
            "and engaging narrative arcs. You can spot when a paper jumps topics abruptly, "
            "when sections don't connect well, or when the reading experience is jarring."
        ),
        llm=llm,
        tools=[],
        verbose=True,
        allow_delegation=False,
        max_iter=3,
        max_retry_limit=1,
    )
