from crewai import Task
from crewai import Agent


def create_proofreading_task(agent: Agent, text: str) -> Task:
    # OPTIMIZED: Ask only for key issues instead of full rewrite to save tokens
    return Task(
        description=(
            "Identify top 5 proofreading issues (grammar, clarity, tone) in this research text. "
            "Do NOT rewrite the entire text—just list problems and suggest fixes.\n\n"
            f"{text[:3000]}"  # Truncate to first 3000 chars to reduce token usage
        ),
        expected_output="A concise list of 5 key proofreading issues with brief fix suggestions.",
        agent=agent,
    )
