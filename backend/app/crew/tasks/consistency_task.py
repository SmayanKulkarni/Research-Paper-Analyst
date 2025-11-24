from crewai import Task


def create_consistency_task(agent, text: str) -> Task:
    return Task(
        description=(
            "Scan this research text for internal inconsistencies, conflicting statements, "
            "terminology mismatches, and mismatched references:\n\n"
            f"{text}"
        ),
        expected_output="A consistency report describing each issue and how to fix it.",
        agent=agent,
    )
