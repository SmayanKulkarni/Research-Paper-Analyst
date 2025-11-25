from crewai import Task


def create_structure_task(agent, text: str) -> Task:
    # OPTIMIZED: Truncate text and ask for summary of top issues only
    return Task(
        description=(
            "Review the structure and logical flow. Point out top 3 structural issues "
            "(missing sections, unclear transitions, reordering needs). Be concise.\n\n"
            f"{text[:3000]}"
        ),
        expected_output="A concise summary of top 3 structural issues with brief fix suggestions.",
        agent=agent,
    )
