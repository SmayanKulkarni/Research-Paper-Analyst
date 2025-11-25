from crewai import Agent
from app.crew.tools.plagiarism_tool import plagiarism_tool
from app.services.llm_provider import get_crewai_llm


# Plagiarism agent should be conservative with tokens; use lower max_tokens
llm = get_crewai_llm(temperature=0.5, max_tokens=128)


def create_plagiarism_agent() -> Agent:
    return Agent(
        role="Plagiarism and Similarity Analyst",
        goal=(
            "Use the plagiarism tool to identify overlapping or paraphrased content "
            "between the current paper and previously indexed works."
        ),
        backstory=(
            "You are an academic integrity officer with access to a semantic search index "
            "of many research papers."
        ),
        llm=llm,
        tools=[plagiarism_tool],
        verbose=True,
        allow_delegation=False,
    )