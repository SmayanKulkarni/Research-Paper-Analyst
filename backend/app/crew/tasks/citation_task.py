from crewai import Task


def create_citation_task(agent, text: str) -> Task:
    return Task(
        description=(
            "Check this research text for missing citations, incorrect references, "
            "and uncredited claims. Highlight where citations should be added:\n\n"
            f"{text}"
        ),
        expected_output="A citation report listing issues and suggested citation locations.",
        agent=agent,
    )
