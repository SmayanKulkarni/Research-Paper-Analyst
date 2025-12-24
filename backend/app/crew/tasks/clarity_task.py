"""
Clarity of Thought Task

Analyzes logical reasoning and argument clarity in research papers.
"""

from crewai import Task


def create_clarity_task(agent, text: str) -> Task:
    """
    Create a clarity of thought analysis task.
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
            "Analyze the CLARITY OF THOUGHT and LOGICAL REASONING in this research paper.\n\n"
            "## Your Task:\n"
            "Evaluate how clearly and logically the authors present their ideas:\n\n"
            "### 1. Main Argument Clarity\n"
            "- Is the main thesis/hypothesis clearly stated?\n"
            "- Can you easily identify what problem the paper addresses?\n"
            "- Are the research questions well-defined?\n\n"
            "### 2. Logical Reasoning\n"
            "- Do the conclusions follow logically from the premises?\n"
            "- Are there logical gaps or unjustified leaps?\n"
            "- Is the chain of reasoning easy to follow?\n"
            "- Are assumptions made explicit?\n\n"
            "### 3. Explanation Quality\n"
            "- Are key concepts clearly defined?\n"
            "- Are complex ideas broken down effectively?\n"
            "- Do examples and illustrations aid understanding?\n"
            "- Are technical terms explained when first introduced?\n\n"
            "### 4. Argument Strength\n"
            "- Are claims well-supported by evidence?\n"
            "- Are counter-arguments acknowledged?\n"
            "- Is the reasoning rigorous?\n"
            "- Are limitations honestly discussed?\n\n"
            "### 5. Clarity Issues\n"
            "Identify specific passages that are:\n"
            "- Vague or ambiguous\n"
            "- Overly complex for no reason\n"
            "- Logically unclear\n"
            "- Missing key explanations\n"
            f"{truncation_note}\n"
            "---PAPER TEXT---\n"
            f"{text}\n"
            "---END OF PAPER---"
        ),
        expected_output=(
            "A comprehensive clarity analysis including:\n"
            "1. Overall clarity score (1-10)\n"
            "2. Assessment of main argument clarity\n"
            "3. Analysis of logical reasoning quality\n"
            "4. Specific examples of unclear or illogical passages\n"
            "5. Recommendations for improving clarity and logical flow"
        ),
        agent=agent,
        context=None,
    )
