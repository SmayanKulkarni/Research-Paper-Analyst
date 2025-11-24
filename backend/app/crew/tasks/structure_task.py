from crewai import Task


def create_structure_task(agent, text: str) -> Task:
    return Task(
        description=(
            "Analyze the structure, sectioning, and logical flow of this research text. "
            "Point out missing sections, unclear transitions, and structural issues:\n\n"
            f"{text}"
        ),
        expected_output="A detailed structure review with specific recommendations for reordering and improving sections.",
        agent=agent,
    )
