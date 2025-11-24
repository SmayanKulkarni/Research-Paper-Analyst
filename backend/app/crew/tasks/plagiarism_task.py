from crewai import Task


def create_plagiarism_task(agent, text: str) -> Task:
    return Task(
        description=(
            "Use your plagiarism tool to check this research text for semantic similarity "
            "and paraphrased content compared to indexed papers:\n\n"
            f"{text}"
        ),
        expected_output="A plagiarism and similarity report with sources and similarity scores.",
        agent=agent,
    )
