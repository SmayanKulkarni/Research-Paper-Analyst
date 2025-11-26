# backend/app/crew/tasks/plagiarism_task.py
from crewai import Task

def create_plagiarism_task(agent, text: str) -> Task:
    # Truncate text to avoid RateLimitError (Groq TPM limit is ~12k)
    # 25,000 chars is roughly 6k-7k tokens, leaving buffer for the response.
    max_chars = 25000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...[Text truncated due to API rate limits]..."

    return Task(
        description=(
            "Use your plagiarism tool to check this research text for semantic similarity "
            "and paraphrased content compared to indexed papers:\n\n"
            f"{text}"
        ),
        expected_output="A plagiarism and similarity report with sources and similarity scores.",
        agent=agent,
    )