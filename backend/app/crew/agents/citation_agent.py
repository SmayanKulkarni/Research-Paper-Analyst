import os
from crewai import Agent, LLM, Task, Crew
from dotenv import load_dotenv
load_dotenv()


llm = LLM(
    model="groq/openai/gpt-oss-120b",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.3
)

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


