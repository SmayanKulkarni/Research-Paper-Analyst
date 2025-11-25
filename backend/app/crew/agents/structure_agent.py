import os
from crewai import Agent, LLM, Task, Crew
from dotenv import load_dotenv
load_dotenv()


llm = LLM(
    model="groq/openai/gpt-oss-120b",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.2
)

def create_structure_agent() -> Agent:
    return Agent(
        role="Research Structure Analyst",
        goal=(
            "Evaluate and improve the overall structure, section flow, and organization "
            "of research papers."
        ),
        backstory=(
            "You are a senior reviewer who focuses on whether papers are logically "
            "organized, with clear sections, contributions, and conclusions."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )