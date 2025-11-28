from crewai import Agent
from app.services.llm_provider import get_crewai_llm
from app.config import get_settings


def create_citation_agent() -> Agent:
    settings = get_settings()
    # Citation agent uses llama-3.1-8b-instant (lightweight, fast)
    llm = get_crewai_llm(model=settings.CREW_CITATION_MODEL, temperature=0.25, max_tokens=3000)
    
    return Agent(
        role="Citation and Referencing Specialist",
        goal=(
            "Identify missing citations, incorrect referencing, and uncredited claims "
            "in research manuscripts. Make sure that the citations are accurate and well written according to IEEE format."
            "Give output in a clear and concise no nonsense way."
        ),
        backstory=(
            "You are meticulous about academic honesty, familiar with common citation "
            "styles and best practices for attribution."
            "You read the citations in depth with interest"
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


