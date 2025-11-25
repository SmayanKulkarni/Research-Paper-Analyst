import os
from crewai import Agent, LLM, Task, Crew
from dotenv import load_dotenv
load_dotenv()


llm = LLM(
    model="groq/openai/gpt-oss-120b",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.3
)

def create_consistency_agent() -> Agent:
    return Agent(
        role="Consistency and Coherence Checker",
        goal=(
            "Detect contradictions, inconsistent terminology, and mismatched references "
            "across the research paper."
        ),
        backstory=(
            "You specialize in reading entire manuscripts end-to-end to ensure that "
            "definitions, symbols, and claims stay consistent."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )