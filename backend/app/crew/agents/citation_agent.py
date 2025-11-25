from crewai import Agent
from app.services.llm_provider import get_crewai_llm


# Citation checks can be shorter; constrain max_tokens to reduce token usage
llm = get_crewai_llm(temperature=0.25, max_tokens=128)


def create_citation_agent() -> Agent:
    return Agent(
        role="Citation and Referencing Specialist",
        goal=(
            "Identify missing citations, incorrect referencing, and uncredited claims "
            "in research manuscripts."
        ),
        backstory=(
            "You are meticulous about academic honesty, familiar with common citation "
            "styles and best practices for attribution."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


