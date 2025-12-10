"""
Plagiarism Task - Task definition for the plagiarism detection agent.
"""

from crewai import Task


def create_plagiarism_task(agent, text: str) -> Task:
    """
    Create a plagiarism detection task.
    Searches for similar papers and analyzes content overlap.
    
    Args:
        agent: The plagiarism agent that will execute this task
        text: The full paper text to check for plagiarism
        
    Returns:
        CrewAI Task for plagiarism detection
    """
    # Use abstract/intro for searching (first 8000 chars typically contains key claims)
    search_text = text[:8000]
    
    return Task(
        description=(
            "Check this paper for plagiarism using the 'Academic Paper Search' tool.\n\n"
            "1. Call the tool with the paper text\n"
            "2. If similar papers found: briefly analyze if properly cited\n"
            "3. If no papers found: report HIGH originality\n"
            "4. Rate originality: High/Medium/Low/Concern\n\n"
            "IMPORTANT: If the tool returns a complete assessment, you can use it directly.\n\n"
            f"---PAPER---\n{search_text}\n---END---"
        ),
        expected_output=(
            "Brief plagiarism report:\n"
            "- Similar papers found: [number]\n"
            "- Key similarities (if any)\n"
            "- Originality: [High/Medium/Low/Concern]\n"
            "- Recommendation"
        ),
        agent=agent,
        context=None,
    )
