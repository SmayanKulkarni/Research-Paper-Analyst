import os
from crewai import Agent, LLM, Task, Crew
from dotenv import load_dotenv
load_dotenv()


llm = LLM(
    model="groq/openai/gpt-oss-120b",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.3
)

def create_proofreader() -> Agent:
    return Agent(
        role="Academic Proofreader",
        goal=(
            "Improve clarity, grammar, coherence, and academic tone in research papers "
            "while preserving the original meaning."
        ),
        backstory=(
            "You are an expert academic editor with years of experience refining "
            "conference and journal submissions across computer science and engineering."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )