from crewai import Task


def create_structure_task(agent, text: str, section_headings: str = None) -> Task:
    """
    Create a comprehensive structure analysis task.
    
    This task analyzes document organization using the FULL paper text
    plus extracted section headings for quick reference.
    
    Args:
        agent: The structure analyst agent
        text: Full paper text for comprehensive analysis
        section_headings: Optional extracted section headings for quick reference
    
    Returns:
        CrewAI Task for structure analysis
    """
    headings_section = ""
    if section_headings:
        headings_section = f"\n**Quick Reference - Detected Headings:**\n{section_headings}\n"
    
    return Task(
        description=(
            "Perform a COMPREHENSIVE STRUCTURE ANALYSIS of this research paper.\n\n"
            f"{headings_section}\n"
            "## Analysis Requirements:\n\n"
            "### 1. Section Presence & Completeness\n"
            "Check for all standard academic paper sections:\n"
            "- Title and Abstract\n"
            "- Introduction (problem statement, motivation, contributions)\n"
            "- Related Work / Background / Literature Review\n"
            "- Methodology / Methods / Approach\n"
            "- Experiments / Evaluation / Results\n"
            "- Discussion / Analysis\n"
            "- Conclusion / Future Work\n"
            "- References\n"
            "- Appendices (if applicable)\n\n"
            "### 2. Logical Flow Analysis\n"
            "- Does the paper flow logically from problem → solution → evaluation?\n"
            "- Are transitions between sections smooth?\n"
            "- Is there a clear narrative thread throughout?\n\n"
            "### 3. Section Quality Assessment\n"
            "For each major section, assess:\n"
            "- Is it appropriately sized (not too short/long)?\n"
            "- Does it contain expected content?\n"
            "- Is subsection organization appropriate?\n\n"
            "### 4. Academic Convention Compliance\n"
            "- Does structure follow field-specific conventions?\n"
            "- Are figures/tables properly placed and referenced?\n"
            "- Is the abstract properly structured (background, method, results, conclusion)?\n\n"
            "### 5. Recommendations\n"
            "Provide specific, actionable recommendations for improving structure.\n\n"
            "Formatting Rules:\n"
            "- Do NOT include internal thoughts, chain-of-thought, or meta commentary.\n"
            "- Do NOT include headings like 'Thought', 'Reasoning', or 'Final Answer'.\n"
            "- Return only the structured report with the following top-level sections: Section Presence & Completeness; Logical Flow Analysis; Section Quality Assessment; Academic Convention Compliance; Recommendations.\n\n"
            "---FULL PAPER TEXT---\n"
            f"{text}\n"
            "---END OF PAPER---"
        ),
        expected_output=(
            "A comprehensive structure analysis report including:\n"
            "1. Section inventory (present/missing/incomplete)\n"
            "2. Flow and coherence assessment\n"
            "3. Section-by-section quality notes\n"
            "4. Convention compliance score\n"
            "5. Prioritized list of structural improvements. Do not include any meta or internal reasoning."
        ),
        agent=agent,
        context=None,
    )
