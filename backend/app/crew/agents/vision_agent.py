import os
from crewai import Agent, LLM, Task, Crew
from dotenv import load_dotenv
load_dotenv()
from app.crew.tools.vision_tool import vision_tool



llm = LLM(
    model="groq/meta-llama/llama-4-scout-17b-16e-instruct",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.2
)

def create_vision_agent():
    return Agent(
        role="Scientific Image Reviewer",
        backstory=(
            "You are skilled at interpreting scientific figures, charts, and diagrams "
            "to assess their clarity, accuracy, and relevance to the accompanying text."
        ),
        goal="Analyze figures using a vision model.",
        llm=llm,
        tools=[vision_tool],
        verbose=True
    )