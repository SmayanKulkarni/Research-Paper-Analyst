from crewai import Task

def create_citation_task(agent, text: str) -> Task:
    # UNLIMITED MODE: No truncation.
    return Task(
        description=(
            "You are a Citation Auditor. Your goal is to verify specific claims.\n"
            "INSTRUCTIONS:\n"
            "1. Find sentences in the text that use citations (e.g., [1], (Smith, 2020)).\n"
            "2. Extract the bibliography entry for that citation.\n"
            "3. USE the 'Citation Integrity Checker' tool to verify if the real paper supports the claim.\n"
            "4. Your output must be a list of: Claim -> Cited Paper -> Verdict (Supported/Unsupported).\n"
            "5. If you cannot check a citation, mark it as 'Unverified'.\n\n"
            f"TEXT CONTENT:\n{text}"
        ),
        expected_output="A verification report of citations with Supported/Unsupported verdicts.",
        agent=agent,
    )