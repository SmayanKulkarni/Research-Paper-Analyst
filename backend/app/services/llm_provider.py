from typing import Optional
import os

from crewai import LLM

from app.config import get_settings
from app.utils.logging import logger

settings = get_settings()

# Set GROQ_API_KEY in environment for LiteLLM routing
os.environ["GROQ_API_KEY"] = settings.GROQ_API_KEY


def _ensure_groq_prefix(model: str) -> str:
    """Ensure model has groq/ prefix for LiteLLM routing."""
    if not model.startswith("groq/"):
        return f"groq/{model}"
    return model


def get_crewai_llm(
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
):
    """
    Get a CrewAI LLM instance that routes to Groq via LiteLLM.
    
    Model names must have "groq/" prefix for LiteLLM routing.
    Example: "groq/llama-3.1-8b-instant" routes to Groq's Llama model.
    """
    if model is None:
        model = settings.GROQ_GPT_OSS_MODEL

    model = _ensure_groq_prefix(model)

    if max_tokens is None:
        max_tokens = settings.MAX_COMPLETION_TOKENS

    return LLM(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def get_crewai_vision_llm(
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: Optional[int] = None,
):
    """
    Get a CrewAI LLM instance for vision tasks.
    
    Uses Groq's native vision model via LiteLLM routing.
    """
    if model is None:
        model = settings.GROQ_VISION_MODEL

    model = _ensure_groq_prefix(model)
    
    if max_tokens is None:
        max_tokens = settings.MAX_VISION_TOKENS

    return LLM(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
