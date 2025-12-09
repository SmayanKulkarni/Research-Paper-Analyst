from crewai import Task


def create_citation_task(agent, text: str) -> Task:
    """
    Create a citation verification task - quick check of 3-5 citations.
    """
    return Task(
        description=(
            "QUICK citation check - verify only 3-5 key citations.\n\n"
            "IMPORTANT RULES:\n"
            "- Call the tool ONCE per citation\n"
            "- If tool returns 'not found', mark as 'unverified' and MOVE ON\n"
            "- Do NOT retry failed lookups\n"
            "- After checking 3-5 citations, write your final report\n\n"
            "Steps:\n"
            "1. Find 3-5 important claims with citations\n"
            "2. For each: call tool ONCE, record result\n"
            "3. Write final report and FINISH\n\n"
            "---PAPER (first 15000 chars)---\n"
            f"{text[:15000]}\n"
            "---END---"
        ),
        expected_output=(
            "Brief citation report: verified count, unverified count, any issues found."
        ),
        agent=agent,
        context=None,
    )
