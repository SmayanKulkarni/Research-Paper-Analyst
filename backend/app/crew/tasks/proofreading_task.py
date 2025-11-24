from crewai import Task
from crewai import Agent


def create_proofreading_task(agent: Agent, text: str) -> Task:
    return Task(
        description=(
            "Proofread the following research text for clarity, grammar, and academic tone. "
            "Return an improved version and briefly explain key changes.\n\n"
            f"{text}"
        ),
        expected_output="A polished version of the text plus a short explanation of edits.",
        agent=agent,
    )
