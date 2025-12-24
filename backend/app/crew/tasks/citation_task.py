from crewai import Task


def create_citation_task(agent, text: str) -> Task:
    """
    Create a citation-reference consistency check task.
    Verifies that all citations in the paper have references and vice versa.
    No external API calls - purely internal consistency checking.
    """
    # Truncate text if too long for context
    max_text_length = 50000
    truncated = len(text) > max_text_length
    if truncated:
        text = text[:max_text_length]
    
    truncation_note = ""
    if truncated:
        truncation_note = "\nNote: Paper text was truncated for analysis. Focus on the provided content.\n"
    
    return Task(
        description=(
            "Check CITATION-REFERENCE CONSISTENCY in this research paper.\n\n"
            "## Your Task:\n"
            "Use the Citation Reference Checker tool to verify:\n\n"
            "### 1. All Citations Have References\n"
            "- Check that every citation like [1], [2], [3] in the paper content\n"
            "  has a corresponding entry in the References section\n"
            "- Identify any citations that point to non-existent references\n\n"
            "### 2. All References Are Cited\n"
            "- Check that every reference in the References section\n"
            "  is actually cited somewhere in the paper\n"
            "- Identify any unused references\n\n"
            "### 3. Citation Numbering\n"
            "- Check for gaps in citation numbering (e.g., [1], [2], [4] - missing [3])\n"
            "- Identify any broken or malformed citations\n\n"
            "## Quick Checklist (apply before approving any citation)\n"
            "For a sample of key citations and any flagged ones, assess:\n"
            "1) Support: Does the cited source support the specific claim it is attached to?\n"
            "2) Credibility: Is the source credible (peer-reviewed venue, reputable conference/journal, recognized preprint server)?\n"
            "3) Fair Representation: Is the source accurately and fairly represented (no over-claims, correct attribution)?\n"
            "4) Formatting: Is the citation properly formatted and consistent with the paper's style (numeric vs author-year, ordering)?\n"
            "5) Currency & Access: Is the reference reasonably current for the field and accessible (DOI, URL present if relevant)?\n\n"
            "## Tool Usage:\n"
            "- Call the 'Citation Reference Checker' tool ONCE with the full paper text\n"
            "- The tool will analyze the paper and return a detailed consistency report\n"
            "- Use the tool output to form your final analysis\n"
            "\nFormatting Rules:\n"
            "- Do NOT include internal thoughts, chain-of-thought, or meta commentary.\n"
            "- Do NOT include headings like 'Thought', 'Reasoning', or 'Final Answer'.\n"
            "- Return only the structured report with the following sections: Summary; Citations Without References; References Not Cited; Numbering Issues; Consistency Assessment; Quick Checklist Summary.\n"
            f"{truncation_note}\n"
            "---FULL PAPER TEXT---\n"
            f"{text}\n"
            "---END OF PAPER---"
        ),
        expected_output=(
            "A citation-reference consistency report including:\n"
            "1. Total number of citations found in text\n"
            "2. Total number of references in reference list\n"
            "3. Any citations without corresponding references\n"
            "4. Any references not cited in the paper\n"
            "5. Assessment of citation consistency (Good/Minor Issues/Needs Attention). Do not include any meta or internal reasoning.\n"
            "6. Quick Checklist Summary with any flagged citations (Support, Credibility, Fair Representation, Formatting, Currency & Access)"
        ),
        agent=agent,
        context=None,
    )
