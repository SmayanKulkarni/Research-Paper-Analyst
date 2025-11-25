import os
from crewai import Agent, LLM, Task, Crew
from dotenv import load_dotenv
load_dotenv()
from app.crew.tools.plagiarism_tool import plagiarism_tool


llm = LLM(
    model="groq/openai/gpt-oss-120b",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.7
)


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