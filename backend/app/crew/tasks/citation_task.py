from crewai import Task


def create_citation_task(agent, text: str) -> Task:
    # OPTIMIZED: Truncate text to first 3000 chars; ask for issues only, not full report
    return Task(
        description=(
            "Identify top 5 citation issues (missing refs, uncredited claims) in this text. "
            "Be concise—just list the issues and suggested fixes.\n\n"
            f"{text[:3000]}"
        ),
        expected_output="A concise list of top 5 citation issues with fix suggestions.",
        agent=agent,
    )
