from crewai import Task

def create_citation_task(agent, text: str) -> Task:
    return Task(
        description=(
            "Analyze the text for citation integrity.\n"
            "1. Identify 3-5 key claims that rely on citations (e.g., [1], (Smith, 2020)).\n"
            "2. Extract the corresponding reference string from the bibliography (if provided in text).\n"
            "3. USE YOUR TOOL 'Citation Integrity Checker' to verify if the real paper supports the claim.\n"
            "4. Also check for formatting consistency.\n\n"
            f"TEXT CONTENT:\n{text[:15000]}..." # Reminder: Text might be truncated if not using full mode
        ),
        expected_output="A report listing verified vs. suspicious citations, formatting errors, and missing references.",
        agent=agent,
    )