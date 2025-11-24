from langchain_groq import ChatGroq
from app.config import get_settings

settings = get_settings()

groq_llm = ChatGroq(
    api_key=settings.GROQ_API_KEY,
    model_name="llama-3.1-70b-versatile",
    temperature=0.1,
    max_tokens=4096
)

vision_llm = ChatGroq(
    api_key=settings.GROQ_API_KEY,
    model_name="llama-4-scout-17b-16e-instruct",
    temperature=0.1,
    max_tokens=4096
)
