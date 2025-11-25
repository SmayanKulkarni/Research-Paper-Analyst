from typing import List

from crewai import Task


def create_vision_task(agent, images: List[str]) -> Task:
    return Task(
        description=(
            "Analyze the scientific figures and tables at these paths:\n"
            f"{', '.join(images)}\n\n"
            "Check: clarity, labeling, legends, relevance. Suggest improvements."
        ),
        expected_output="Key issues found in figures/tables and specific improvements.",
        agent=agent,
        # OPTIMIZATION: Skip context from prior tasks to avoid message length issues
        context=None,
    )
