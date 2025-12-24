"""
Clarity of Thought Agent

Analyzes the logical reasoning, argument structure, and clarity of ideas
in a research paper.
"""

from crewai import Agent
from app.services.llm_provider import get_crewai_llm
from app.config import get_settings


def create_clarity_agent(max_tokens: int = None) -> Agent:
    """
    Create a Clarity of Thought Analysis Agent.
    
    This agent evaluates:
    - Logical reasoning and argument coherence
    - Clarity of main ideas and hypotheses
    - Quality of explanations and definitions
    - Strength of conclusions from premises
    
    Args:
        max_tokens: Dynamic token limit based on paper length
    
    Returns:
        CrewAI Agent for clarity analysis
    """
    settings = get_settings()
    
    if max_tokens is None:
        max_tokens = settings.MAX_COMPLETION_TOKENS
    
    llm = get_crewai_llm(
        model=settings.CREW_CLARITY_MODEL,
        temperature=0.2,
        max_tokens=max_tokens,
    )
    
    return Agent(
        role="Clarity of Thought Specialist",
        goal=(
            "Analyze the paper's logical reasoning, argument structure, and clarity of ideas. "
            "Identify unclear explanations, weak arguments, logical gaps, and areas where "
            "the author's thinking could be more explicit or better organized."
        ),
        backstory=(
            "You are an expert in logic, critical thinking, and scientific communication. "
            "You have a PhD in philosophy of science, especially all fields of computer science and engineering,and have reviewed thousands of research "
            "papers. You excel at identifying unclear reasoning, spotting logical fallacies, "
            "and recognizing when authors make unjustified leaps in their arguments. You help "
            "researchers clarify their thinking and strengthen their intellectual contributions."
        ),
        llm=llm,
        tools=[],
        verbose=True,
        allow_delegation=False,
        max_iter=3,
        max_retry_limit=1,
    )
