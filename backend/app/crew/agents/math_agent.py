"""
Math Review Agent - Analyzes mathematical content in research papers.

Reviews equations, proofs, derivations, notation consistency,
and mathematical reasoning for correctness and clarity.
"""

from crewai import Agent
from app.config import get_settings

settings = get_settings()


def create_math_review_agent() -> Agent:
    """
    Create a Math Review Agent that analyzes mathematical content.
    
    Responsibilities:
    - Verify equation correctness and derivations
    - Check proof logic and completeness
    - Review notation consistency
    - Assess mathematical clarity and rigor
    - Identify potential errors or ambiguities
    """
    return Agent(
        role="Mathematical Reasoning Specialist",
        goal=(
            "Thoroughly review mathematical content in research papers for correctness, "
            "clarity, and rigor. Identify errors in equations, proofs, and derivations."
        ),
        backstory=(
            "You are a mathematician with expertise in reviewing academic papers. "
            "You have deep knowledge of mathematical notation, proof techniques, "
            "and common errors. You can identify subtle mistakes in derivations "
            "and assess whether mathematical arguments are sound and complete."
        ),
        verbose=True,
        allow_delegation=False,
        llm=settings.CREW_MATH_MODEL,
        max_iter=1,  # Single iteration - no loops
        max_retry_limit=0,  # No retries on failure
        memory=False,  # Disable memory to reduce token usage
    )
