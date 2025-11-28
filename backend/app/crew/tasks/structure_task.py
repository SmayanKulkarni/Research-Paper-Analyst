from crewai import Task

def create_structure_task(agent, text: str) -> Task:
    # UNLIMITED MODE: No truncation.
    return Task(
        description=(
            "Analyze the structure of this research paper against standard academic formats (IMRaD).\n"
            "1. Is the abstract consistent with the conclusion?\n"
            "2. Are the methods described in enough detail?\n"
            "3. Does the flow of arguments make logical sense?\n\n"
            f"{text}"
        ),
        expected_output="A brief report on structural integrity and flow issues.",
        agent=agent,
    )