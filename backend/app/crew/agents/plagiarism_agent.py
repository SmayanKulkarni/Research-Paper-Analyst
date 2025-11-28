from crewai import Agent
from app.crew.tools.plagiarism_tool import plagiarism_tool
from app.services.llm_provider import get_crewai_llm
from app.config import get_settings


def create_plagiarism_agent() -> Agent:
    settings = get_settings()
    # Plagiarism agent uses llama-3.3-70b-versatile (powerful for complex analysis)
    llm = get_crewai_llm(model=settings.CREW_PLAGIARISM_MODEL, temperature=0.5, max_tokens=1000)
    
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