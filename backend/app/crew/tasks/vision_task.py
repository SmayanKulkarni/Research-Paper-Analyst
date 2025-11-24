from typing import List

from crewai import Task


def create_vision_task(agent, images: List[str]) -> Task:
    return Task(
        description=(
            "Analyze the scientific figures and tables located at these file paths:\n"
            f"{images}\n\n"
            "Evaluate clarity, labeling, legends, and whether each visual supports "
            "the claims in the text. Suggest improvements."
        ),
        expected_output="A figure/table analysis report with issues and specific improvement suggestions.",
        agent=agent,
    )
