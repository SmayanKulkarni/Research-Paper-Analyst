from crewai import Task


def create_consistency_task(agent, text: str) -> Task:
    # OPTIMIZED: Truncate and ask for top issues only, not exhaustive report
    return Task(
        description=(
            "Identify top 3 internal inconsistencies (conflicting statements, terminology mismatches) "
            "in this text. Be concise.\n\n"
            f"{text[:3000]}"
        ),
        expected_output="A concise list of top 3 consistency issues with fix suggestions.",
        agent=agent,
    )
