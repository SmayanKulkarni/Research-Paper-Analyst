from crewai import Agent

from app.config import get_settings
from app.crew.tools.plagiarism_tool import plagiarism_tool

settings = get_settings()
GROQ_MODEL = settings.GROQ_MODEL_NAME


def create_plagiarism_agent() -> Agent:
    return Agent(
        role="Plagiarism and Similarity Analyst",
        goal=(
            "Use the plagiarism tool to identify overlapping or paraphrased content "
            "between the current paper and previously indexed works."
        ),
        backstory=(
            "You are an academic integrity officer with access to a semantic search "
            "index of many research papers."
        ),
        llm=GROQ_MODEL,
        tools=[plagiarism_tool],
        verbose=True,
        allow_delegation=False,
    )
