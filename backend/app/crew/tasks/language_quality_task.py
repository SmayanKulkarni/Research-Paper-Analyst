"""
Language Quality Task - Comprehensive grammar, clarity, and style analysis.
"""

from crewai import Task


def create_language_quality_task(agent, text: str) -> Task:
    """
    Comprehensive language quality analysis - accuracy is the priority.
    Analyzes the FULL paper text for thorough review.
    """
    return Task(
        description=(
            "Perform a COMPREHENSIVE language quality review of this research paper.\n\n"
            "Analyze the ENTIRE document for:\n\n"
            "## 1. Grammar & Syntax\n"
            "- Subject-verb agreement errors\n"
            "- Tense consistency issues\n"
            "- Sentence fragments or run-ons\n"
            "- Punctuation errors\n"
            "- Article usage (a/an/the)\n\n"
            "## 2. Clarity & Readability\n"
            "- Ambiguous sentences or phrases\n"
            "- Overly complex sentence structures\n"
            "- Jargon that needs explanation\n"
            "- Passive voice overuse\n"
            "- Unclear pronoun references\n\n"
            "## 3. Academic Style\n"
            "- Consistency of terminology throughout\n"
            "- Appropriate academic tone\n"
            "- Proper use of hedging language\n"
            "- Citation integration quality\n\n"
            "## 4. Consistency Checks\n"
            "- Spelling variations (British vs American)\n"
            "- Acronym definitions and usage\n"
            "- Number formatting consistency\n"
            "- Capitalization patterns\n\n"
            "For EACH issue found, provide:\n"
            "- Location (section/paragraph if identifiable)\n"
            "- The problematic text (quote it)\n"
            "- What the problem is\n"
            "- Suggested correction\n\n"
            "Organize findings by severity: Critical → Major → Minor\n\n"
            "Formatting Rules:\n"
            "- Do NOT include internal thoughts, chain-of-thought, or meta commentary.\n"
            "- Do NOT include headings like 'Thought', 'Reasoning', or 'Final Answer'.\n"
            "- Return only the structured report with the following top-level sections: Grammar & Syntax; Clarity & Readability; Academic Style; Consistency Checks; Recommendations.\n\n"
            "---FULL PAPER TEXT---\n"
            f"{text}\n"
            "---END OF PAPER---"
        ),
        expected_output=(
            "A detailed language quality report organized by category (Grammar & Syntax; Clarity & Readability; Academic Style; Consistency Checks; Recommendations) "
            "with specific issues, their locations, and suggested corrections. Include severity ratings. "
            "Do not include any meta or internal reasoning."
        ),
        agent=agent,
        context=None,
    )
