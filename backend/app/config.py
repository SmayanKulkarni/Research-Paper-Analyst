from functools import lru_cache
from typing import Optional

# Support both Pydantic v1 (BaseSettings in pydantic) and v2 (pydantic-settings)
try:  # Pydantic v2 style
    from pydantic_settings import BaseSettings
except Exception:  # Fallback to Pydantic v1
    from pydantic import BaseSettings  # type: ignore

from pydantic import Field


class Settings(BaseSettings):
    PROJECT_NAME: str = "Research Paper Analyzer"

    # ============================
    # GROQ
    # ============================
    GROQ_API_KEY: str = Field(..., env="GROQ_API_KEY")
    
    # Default model: Groq Llama 3.1 8B (reliable, fast, and cheap)
    GROQ_GPT_OSS_MODEL: str = Field("groq/llama-3.1-8b-instant", env="GROQ_GPT_OSS_MODEL")
    # For vision, keep the Groq vision model
    GROQ_VISION_MODEL: str = Field("groq/llama-3.2-11b-vision-preview", env="GROQ_VISION_MODEL")

    # Per-agent model assignments
    GROQ_CITATION_MODEL: str = Field("groq/llama-3.1-8b-instant", env="GROQ_CITATION_MODEL")
    GROQ_STRUCTURE_MODEL: str = Field("groq/llama-3.1-8b-instant", env="GROQ_STRUCTURE_MODEL")
    GROQ_CONSISTENCY_MODEL: str = Field("groq/llama-3.1-8b-instant", env="GROQ_CONSISTENCY_MODEL")
    GROQ_PLAGIARISM_MODEL: str = Field("groq/llama-3.1-8b-instant", env="GROQ_PLAGIARISM_MODEL")
    GROQ_PROOFREADER_MODEL: str = Field("groq/llama-3.1-8b-instant", env="GROQ_PROOFREADER_MODEL")
    GROQ_MATH_MODEL: str = Field("groq/llama-3.1-8b-instant", env="GROQ_MATH_MODEL")

    # Make OpenAI Key Optional
    OPENAI_API_KEY: Optional[str] = Field(None, env="OPENAI_API_KEY")

    # ============================
    # EMBEDDINGS (local)
    # ============================
    EMBEDDING_MODEL_NAME: str = Field("BAAI/bge-large-en", env="EMBEDDING_MODEL_NAME")
    EMBEDDING_DIM: int = Field(1024, env="EMBEDDING_DIM")

    # ============================
    # DYNAMIC TOKEN BUDGET (Accuracy-First Approach)
    # ============================
    MAX_TOKEN_BUDGET: int = Field(300000, env="MAX_TOKEN_BUDGET")
    MIN_TOKENS_PER_AGENT: int = Field(5000, env="MIN_TOKENS_PER_AGENT")
    MAX_COMPLETION_TOKENS: int = Field(4096, env="MAX_COMPLETION_TOKENS")
    
    # Vision-specific settings
    MAX_VISION_TOKENS: int = Field(2000, env="MAX_VISION_TOKENS")
    MAX_IMAGES_TO_ANALYZE: int = Field(15, env="MAX_IMAGES_TO_ANALYZE")
    
    # Token estimation ratio (characters to tokens, roughly 4 chars = 1 token)
    CHARS_PER_TOKEN: int = Field(4, env="CHARS_PER_TOKEN")

    # ============================
    # RATE LIMITING (Groq Free/Dev Tier)
    # ============================
    RATE_LIMIT_DELAY: float = Field(2.0, env="RATE_LIMIT_DELAY")
    MAX_RETRIES: int = Field(1, env="MAX_RETRIES")
    RETRY_DELAY: float = Field(5.0, env="RETRY_DELAY")

    # ============================
    # LOCAL STORAGE
    # ============================
    STORAGE_ROOT: str = Field("storage", env="STORAGE_ROOT")
    UPLOADS_DIR: str = Field("uploads", env="UPLOADS_DIR")
    PARQUET_LOCAL_ROOT: str = Field("storage/parquet_data", env="PARQUET_LOCAL_ROOT")

    def _format_model(self, model: str) -> str:
        """Ensure model string is formatted for CrewAI (groq/model-name)"""
        return model

    @property
    def CREW_CITATION_MODEL(self):
        return self._format_model(self.GROQ_CITATION_MODEL)

    @property
    def CREW_STRUCTURE_MODEL(self):
        return self._format_model(self.GROQ_STRUCTURE_MODEL)

    @property
    def CREW_CONSISTENCY_MODEL(self):
        return self._format_model(self.GROQ_CONSISTENCY_MODEL)

    @property
    def CREW_PLAGIARISM_MODEL(self):
        return self._format_model(self.GROQ_PLAGIARISM_MODEL)

    @property
    def CREW_PROOFREADER_MODEL(self):
        return self._format_model(self.GROQ_PROOFREADER_MODEL)

    @property
    def CREW_MATH_MODEL(self):
        return self._format_model(self.GROQ_MATH_MODEL)

    @property
    def CREW_VISION_MODEL(self):
        return self._format_model(self.GROQ_VISION_MODEL)

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()