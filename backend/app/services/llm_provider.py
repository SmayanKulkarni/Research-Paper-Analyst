from langchain_groq import ChatGroq
from app.config import get_settings

settings = get_settings()

# Generic Text LLM
groq_llm = ChatGroq(
    api_key=settings.GROQ_API_KEY,
    model_name=settings.GROQ_TEXT_MODEL,
    temperature=0.1,
    max_tokens=4096
)

# Vision LLM
vision_llm = ChatGroq(
    api_key=settings.GROQ_API_KEY,
    model_name=settings.GROQ_VISION_MODEL,
    temperature=0.1,
    max_tokens=4096
)

