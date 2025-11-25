from crewai import Task

def create_compression_task(agent, chunk: str):
    return Task(
        description=(
            "Compress the following research paper section while preserving all meaning:\n\n"
            f"{chunk}"
        ),
        expected_output="A compact but accurate summary of this chunk.",
        agent=agent
    )
