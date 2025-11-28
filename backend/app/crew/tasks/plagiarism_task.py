from crewai import Task

def create_plagiarism_task(agent, text: str) -> Task:
    # UNLIMITED MODE: No truncation.
    # The agent will process the full text using the tool.
    return Task(
        description=(
            "You are a Plagiarism Analyst. Your ONLY job is to use the 'Plagiarism Checker' tool.\n"
            "INSTRUCTIONS:\n"
            "1. CALL the tool 'Plagiarism Checker' immediately with the provided text.\n"
            "2. The tool will return a list of matched segments.\n"
            "3. If the list is empty, your final answer must be: 'No significant plagiarism detected.'\n"
            "4. If matches are found, list them clearly: Source Title, Similarity Score, and the Suspicious Text.\n"
            "5. DO NOT provide conversational filler like 'Please wait' or 'I will now analyze'.\n\n"
            f"TEXT CONTENT TO SCAN:\n{text}"
        ),
        expected_output="A structured report of plagiarism matches or a confirmation of no plagiarism.",
        agent=agent,
    )