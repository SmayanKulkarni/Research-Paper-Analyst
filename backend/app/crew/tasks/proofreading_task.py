from crewai import Task

def create_proofreading_task(agent, text: str) -> Task:
    # UNLIMITED MODE: No truncation.
    return Task(
        description=(
            "Proofread the following academic text for grammar, clarity, and academic tone.\n"
            "Provide a list of the top 5 most critical improvements needed.\n"
            "Focus on: awkward phrasing, passive voice misuse, and grammatical errors.\n\n"
            f"{text}"
        ),
        expected_output="A list of top 5 proofreading improvements with 'Original' vs 'Fixed' examples.",
        agent=agent,
    )