from crewai import Task


def create_citation_task(agent, text: str) -> Task:
    """
    Create a comprehensive citation verification task.
    Analyzes ALL citations in the paper for accuracy and proper usage.
    """
    return Task(
        description=(
            "Perform a COMPREHENSIVE CITATION ANALYSIS of this research paper.\n\n"
            "## Your Task:\n"
            "Analyze ALL citations and references in this paper for:\n\n"
            "### 1. Citation Completeness\n"
            "- Identify all claims that need citations but don't have them\n"
            "- Check if key assertions are properly supported\n"
            "- Look for statements like 'studies show' without references\n\n"
            "### 2. Citation Accuracy\n"
            "For the MOST IMPORTANT citations (key claims, foundational work):\n"
            "- Use the citation verification tool to check if they exist\n"
            "- Verify the citation details match what's claimed\n"
            "- Check max 10 of the most critical citations\n\n"
            "### 3. Reference Format Consistency\n"
            "- Are references formatted consistently (same style throughout)?\n"
            "- Check for common format issues (missing DOIs, inconsistent author names)\n"
            "- Identify any malformed references\n\n"
            "### 4. Citation Quality Assessment\n"
            "- Are sources recent enough for the field?\n"
            "- Is there over-reliance on a few sources?\n"
            "- Are seminal works in the field cited?\n"
            "- Is there appropriate self-citation balance?\n\n"
            "### 5. In-text Citation Usage\n"
            "- Are citations used correctly in context?\n"
            "- Check for citation needed vs citation present alignment\n"
            "- Look for [?] or broken citation markers\n\n"
            "## Tool Usage Rules:\n"
            "- Call the citation tool ONCE per citation you want to verify\n"
            "- If tool returns 'not found', mark as 'unable to verify' and continue\n"
            "- Do NOT retry failed lookups\n"
            "- Focus on verifying the most critical citations\n\n"
            "---FULL PAPER TEXT---\n"
            f"{text}\n"
            "---END OF PAPER---"
        ),
        expected_output=(
            "A comprehensive citation analysis report including:\n"
            "1. Total citations count and breakdown by type\n"
            "2. Verification results for key citations (verified/unverified/issues)\n"
            "3. Missing citations (claims without proper references)\n"
            "4. Format consistency assessment\n"
            "5. Citation quality score and recommendations"
        ),
        agent=agent,
        context=None,
    )
