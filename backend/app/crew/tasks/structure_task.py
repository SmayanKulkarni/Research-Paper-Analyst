from crewai import Task


def create_structure_task(agent, section_headings: str) -> Task:
    """
    Create a structure analysis task that examines paper organization.
    
    This task analyzes document organization using extracted section headings.
    This approach reduces token usage while still providing meaningful structure analysis.
    
    Args:
        agent: The structure analyst agent
        section_headings: Extracted section headings from the paper
    
    Returns:
        CrewAI Task for structure analysis
    """
    return Task(
        description=(
            "Analyze the STRUCTURE and ORGANIZATION of this research paper based on its section headings.\n\n"
            "**Extracted Section Headings:**\n"
            f"{section_headings}\n\n"
            "Evaluate:\n"
            "1. **Section Organization**: Are all expected sections present (Abstract, Introduction, "
            "Related Work, Methods/Methodology, Results/Experiments, Discussion, Conclusion)?\n"
            "2. **Logical Flow**: Does the order of sections follow a logical progression?\n"
            "3. **Standard Compliance**: Does the structure follow academic paper conventions?\n"
            "4. **Missing Sections**: Any crucial sections that appear to be missing?\n"
            "5. **Redundant Sections**: Any sections that seem redundant or misplaced?\n\n"
            "Provide a concise analysis with specific recommendations."
        ),
        expected_output=(
            "A structured report with:\n"
            "- Overall structure assessment (Good/Needs Improvement/Poor)\n"
            "- List of present sections\n"
            "- List of missing or recommended sections\n"
            "- Top 3-5 specific recommendations for structural improvement"
        ),
        agent=agent,
        # No context from other tasks - independent analysis
        context=None,
    )
