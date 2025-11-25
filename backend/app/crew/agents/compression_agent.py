import os
from crewai import Agent, LLM, Task, Crew
from dotenv import load_dotenv
load_dotenv()


llm = LLM(
    model="groq/openai/gpt-oss-120b",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.3
)
def create_compression_agent():
    return Agent(
        role="Document Compression Specialist",
        goal=(
            "Summarize and compress long research paper chunks without losing meaning. "
            "Produce compact, information-dense summaries that preserve important details."
        ),
        backstory=(
            "You specialize in condensing long academic texts into concise, accurate summaries. "
            "You never remove important content—only compress."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False
    )
