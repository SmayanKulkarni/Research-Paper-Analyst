"""
Language Quality Task - Quick grammar/clarity check.
"""

from crewai import Task


def create_language_quality_task(agent, text: str) -> Task:
    """
    Quick language quality check - top 5 issues only.
    """
    # Truncate to avoid token explosion
    truncated_text = text[:25000] if len(text) > 25000 else text
    
    return Task(
        description=(
            "QUICK language review - find TOP 5 issues only.\n\n"
            "Scan for:\n"
            "1. Grammar errors (top 2)\n"
            "2. Unclear passages (top 2)\n"
            "3. Terminology inconsistencies (top 1)\n\n"
            "Be BRIEF. One sentence per issue. Finish quickly.\n\n"
            f"---PAPER (first {len(truncated_text)} chars)---\n"
            f"{truncated_text}\n"
            "---END---"
        ),
        expected_output="Brief list of top 5 language issues with locations.",
        agent=agent,
        context=None,
    )
