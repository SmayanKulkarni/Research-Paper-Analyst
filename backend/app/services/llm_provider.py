from typing import Optional

from app.config import get_settings
from app.utils.logging import logger

try:
    from crewai import LLM as CrewLLM
except ImportError:
    CrewLLM = None

settings = get_settings()


def get_crewai_llm(
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
):
    """Get a CrewAI LLM instance for agent tasks."""
    if CrewLLM is None:
        raise RuntimeError("CrewAI is not installed or LLM class not available")

    if model is None:
        model = settings.CREW_CITATION_MODEL

    if max_tokens is None:
        max_tokens = 256

    return CrewLLM(
        model=model,
        api_key=settings.GROQ_API_KEY,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def get_crewai_vision_llm(
    model: Optional[str] = None,
    temperature: float = 0.2,
):
    """Get a CrewAI LLM instance for vision tasks."""
    if CrewLLM is None:
        raise RuntimeError("CrewAI is not installed or LLM class not available")

    if model is None:
        model = settings.CREW_VISION_MODEL

    return CrewLLM(
        model=model,
        api_key=settings.GROQ_API_KEY,
        temperature=temperature,
        max_tokens=500,
    )
