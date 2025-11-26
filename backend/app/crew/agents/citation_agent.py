from crewai import Agent
from app.services.llm_provider import get_crewai_llm
from app.config import get_settings
# Import the new tool
from app.crew.tools.citation_tool import verify_citation_integrity

def create_citation_agent() -> Agent:
    settings = get_settings()
    llm = get_crewai_llm(model=settings.CREW_CITATION_MODEL, temperature=0.1)
    
    return Agent(
        role="Citation and Referencing Specialist",
        goal="Ensure all citations are accurate, correctly formatted, and genuinely support the claims made.",
        backstory=(
            "You are a meticulous academic auditor. Your specialty is catching 'hallucinated' citations "
            "where authors cite a paper that has nothing to do with their claim. "
            "You check both formatting style and semantic integrity."
        ),
        llm=llm,
        # Add the tool here
        tools=[verify_citation_integrity],
        verbose=True,
        allow_delegation=False,
    )