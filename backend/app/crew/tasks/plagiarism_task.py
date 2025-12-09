from crewai import Task
from app.models.agents_output import PlagiarismOutput


def create_plagiarism_task(agent, text: str) -> Task:
    """
    Quick plagiarism check - single tool call.
    """
    # Truncate text to avoid token limits
    truncated_text = text[:20000] if len(text) > 20000 else text
    
    return Task(
        description=(
            "QUICK plagiarism check - ONE tool call only.\n\n"
            "RULES:\n"
            "- Call 'Plagiarism and Similarity Checker' tool ONCE\n"
            "- Report the results immediately\n"
            "- Do NOT retry if tool fails\n"
            "- Finish after ONE tool call\n\n"
            f"Paper text (truncated to {len(truncated_text)} chars):\n"
            f"{truncated_text}\n"
            "---END---"
        ),
        expected_output="Plagiarism check result with similarity score and assessment.",
        output_pydantic=PlagiarismOutput,
        agent=agent,
        context=None,
    )
