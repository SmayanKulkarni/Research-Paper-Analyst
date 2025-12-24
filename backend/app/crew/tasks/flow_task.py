"""
Flow Analysis Task

Analyzes narrative flow and transitions in research papers.
"""

from crewai import Task


def create_flow_task(agent, text: str) -> Task:
    """
    Create a flow analysis task.
    """
    # Truncate text if too long
    max_text_length = 50000
    truncated = len(text) > max_text_length
    if truncated:
        text = text[:max_text_length]
    
    truncation_note = ""
    if truncated:
        truncation_note = "\nNote: Paper text was truncated. Focus on the provided content.\n"
    
    return Task(
        description=(
            "Analyze the NARRATIVE FLOW and READABILITY of this research paper.\n\n"
            "## Your Task:\n"
            "Evaluate how smoothly the paper reads and how well sections connect:\n\n"
            "### 1. Overall Narrative Arc\n"
            "- Does the paper tell a coherent story?\n"
            "- Is there a clear beginning, middle, and end?\n"
            "- Does the paper build momentum toward its conclusion?\n"
            "- Is the reader guided through the content?\n\n"
            "### 2. Transitions Between Sections\n"
            "- Are transitions smooth or abrupt?\n"
            "- Do sections connect logically?\n"
            "- Are transitional phrases used effectively?\n"
            "- Is there clear signposting?\n\n"
            "### 3. Paragraph-Level Flow\n"
            "- Do paragraphs have clear topic sentences?\n"
            "- Are ideas within paragraphs well-organized?\n"
            "- Do paragraphs connect to each other?\n"
            "- Is there good micro-level coherence?\n\n"
            "### 4. Readability\n"
            "- Is the paper easy to follow?\n"
            "- Does the pace feel appropriate?\n"
            "- Are there sections that drag or rush?\n"
            "- Would a reader get lost?\n\n"
            "### 5. Flow Issues\n"
            "Identify specific locations where:\n"
            "- Transitions are jarring or missing\n"
            "- Topics change abruptly\n"
            "- The narrative loses momentum\n"
            "- The reader might feel confused\n"
            "\nFormatting Rules:\n"
            "- Do NOT include internal thoughts, chain-of-thought, or meta commentary.\n"
            "- Do NOT include headings like 'Thought', 'Reasoning', or 'Final Answer'.\n"
            "- Return only the structured report with the following sections: Overall Readability Score; Narrative Arc; Transitions; Paragraph-Level Flow; Readability; Flow Issues; Recommendations.\n"
            f"{truncation_note}\n"
            "---PAPER TEXT---\n"
            f"{text}\n"
            "---END OF PAPER---"
        ),
        expected_output=(
            "A comprehensive flow analysis including:\n"
            "1. Overall readability score (1-10)\n"
            "2. Assessment of narrative arc and structure\n"
            "3. Analysis of transitions quality\n"
            "4. Specific examples of flow problems\n"
            "5. Recommendations for improving narrative flow and readability. Do not include any meta or internal reasoning."
        ),
        agent=agent,
        context=None,
    )
