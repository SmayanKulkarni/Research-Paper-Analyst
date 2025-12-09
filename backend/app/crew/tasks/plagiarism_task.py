from crewai import Task
from app.models.agents_output import PlagiarismOutput


def create_plagiarism_task(agent, text: str) -> Task:
    """
    Comprehensive plagiarism and originality check using both
    vector similarity search and web search.
    """
    return Task(
        description=(
            "Perform a COMPREHENSIVE PLAGIARISM AND ORIGINALITY CHECK on this research paper.\n\n"
            "## Analysis Methods:\n"
            "You have access to the 'Plagiarism and Similarity Checker' tool which:\n"
            "1. Searches against a database of academic papers (vector similarity)\n"
            "2. Performs live web search for potentially matching content\n\n"
            "## Your Task:\n"
            "1. Call the plagiarism checker tool with the paper text\n"
            "2. Analyze the results thoroughly\n"
            "3. Provide a detailed originality assessment\n\n"
            "## What to Report:\n\n"
            "### 1. Overall Originality Score\n"
            "- Percentage of original content\n"
            "- Risk assessment (Safe / Low Risk / Suspicious / High Risk)\n\n"
            "### 2. Similarity Matches Found\n"
            "For each significant match:\n"
            "- Source (title, URL if available)\n"
            "- Similarity score\n"
            "- Which section of the paper matches\n"
            "- Detection method (VectorDB or WebSearch)\n\n"
            "### 3. Analysis by Section\n"
            "- Which sections have highest similarity?\n"
            "- Are matches in expected places (common terminology, quotes)?\n"
            "- Are there concerning matches in methodology/results?\n\n"
            "### 4. Recommendations\n"
            "- If issues found, suggest how to address them\n"
            "- Note any properly quoted/cited similar content\n"
            "- Distinguish between plagiarism vs. appropriate citation\n\n"
            "## Tool Usage:\n"
            "- Call the tool ONCE with the full paper text\n"
            "- The tool will return comprehensive results\n"
            "- Do NOT retry if tool encounters issues\n\n"
            "---FULL PAPER TEXT---\n"
            f"{text}\n"
            "---END OF PAPER---"
        ),
        expected_output=(
            "A comprehensive plagiarism report including:\n"
            "1. Overall originality assessment and risk level\n"
            "2. Detailed list of similarity matches (if any)\n"
            "3. Section-by-section analysis\n"
            "4. Recommendations for addressing any issues"
        ),
        output_pydantic=PlagiarismOutput,
        agent=agent,
        context=None,
    )
