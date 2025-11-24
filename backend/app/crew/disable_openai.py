import os

# Completely disable OpenAI fallback
os.environ["OPENAI_API_KEY"] = ""
os.environ["CREWAI_DISABLE_OPENAI"] = "true"
os.environ["CREWAI_LLM_PROVIDER"] = "groq"
