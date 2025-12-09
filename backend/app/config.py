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
    # Using "groq/" prefix for LiteLLM routing (CrewAI uses LiteLLM internally)
    # Note: openai/gpt-oss-20b returns empty on simple prompts - use llama for reliability
    GROQ_GPT_OSS_MODEL: str = Field("groq/llama-3.1-8b-instant", env="GROQ_GPT_OSS_MODEL")
    # For vision, keep the Groq vision model
    GROQ_VISION_MODEL: str = Field("groq/llama-3.2-11b-vision-preview", env="GROQ_VISION_MODEL")

    # Route all agents to llama model by default (can override via env)
    GROQ_CITATION_MODEL: str = Field("groq/llama-3.1-8b-instant", env="GROQ_CITATION_MODEL")
    GROQ_STRUCTURE_MODEL: str = Field("groq/llama-3.1-8b-instant", env="GROQ_STRUCTURE_MODEL")
    GROQ_CONSISTENCY_MODEL: str = Field("groq/llama-3.1-8b-instant", env="GROQ_CONSISTENCY_MODEL")
    GROQ_PLAGIARISM_MODEL: str = Field("groq/llama-3.1-8b-instant", env="GROQ_PLAGIARISM_MODEL")
    GROQ_PROOFREADER_MODEL: str = Field("groq/llama-3.1-8b-instant", env="GROQ_PROOFREADER_MODEL")

    # Make OpenAI Key Optional
    OPENAI_API_KEY: Optional[str] = Field(None, env="OPENAI_API_KEY")

    # ============================
    # PINECONE & SEARCH
    # ============================
    PINECONE_API_KEY: str = Field(..., env="PINECONE_API_KEY")
    PINECONE_ENVIRONMENT: str = Field(..., env="PINECONE_ENVIRONMENT")
    PINECONE_INDEX_NAME: str = Field("research-plagiarism", env="PINECONE_INDEX_NAME")
    
    # ADDED: Missing field causing the crash
    CROSS_ENCODER_MODEL: str = Field("cross-encoder/ms-marco-MiniLM-L-6-v2", env="CROSS_ENCODER_MODEL")
    
    # ============================
    # EMBEDDINGS (local)
    # ============================
    EMBEDDING_MODEL_NAME: str = Field("BAAI/bge-large-en", env="EMBEDDING_MODEL_NAME")
    EMBEDDING_DIM: int = Field(1024, env="EMBEDDING_DIM")

    # ============================
    # PROCESSING CONFIG
    # ============================
    PLAGIARISM_CHUNK_SIZE: int = Field(256, env="PLAGIARISM_CHUNK_SIZE")
    PLAGIARISM_CHUNK_OVERLAP: int = Field(50, env="PLAGIARISM_CHUNK_OVERLAP")

    # ============================
    # TOKEN & COST LIMITS (Budget ≈ ₹20 per run)
    # Groq Dev Tier Pricing (very cheap):
    # - Llama 3.1 8B: Input $0.05/M, Output $0.08/M
    # - Llama 3.2 11B Vision: Input $0.07/M, Output $0.07/M
    # With ₹20 (~$0.24), we can afford ~3M tokens easily
    # ============================
    MAX_COMPLETION_TOKENS: int = Field(1024, env="MAX_COMPLETION_TOKENS")
    MAX_INPUT_TOKENS_HINT: int = Field(4000, env="MAX_INPUT_TOKENS_HINT")  # used for truncation heuristics
    
    # Vision-specific token limits
    MAX_VISION_TOKENS: int = Field(500, env="MAX_VISION_TOKENS")  # Per image analysis
    MAX_IMAGES_TO_ANALYZE: int = Field(10, env="MAX_IMAGES_TO_ANALYZE")

    # ============================
    # RATE LIMITING (Groq Free/Dev Tier)
    # Groq has strict rate limits on free tier:
    # - ~30 requests/minute for Llama 3.1 8B
    # - ~6000 tokens/minute (TPM)
    # Add delays between agent calls to avoid 429 errors
    # ============================
    RATE_LIMIT_DELAY: float = Field(2.0, env="RATE_LIMIT_DELAY")  # Seconds between agent calls
    MAX_RETRIES: int = Field(1, env="MAX_RETRIES")  # Minimal retries - fail fast
    RETRY_DELAY: float = Field(5.0, env="RETRY_DELAY")  # Short delay on retry

    # ============================
    # LOCAL STORAGE
    # ============================
    STORAGE_ROOT: str = Field("storage", env="STORAGE_ROOT")
    UPLOADS_DIR: str = Field("uploads", env="UPLOADS_DIR")
    # ADDED: Missing field for Parquet storage
    PARQUET_LOCAL_ROOT: str = Field("storage/parquet_data", env="PARQUET_LOCAL_ROOT")

    def _format_model(self, model: str) -> str:
        """Ensure model string is formatted for CrewAI (groq/model-name)"""
        # Groq client accepts both "groq/..." and vendor-prefixed models like "openai/..."
        # Keep as-is to allow "openai/gpt-oss-20b".
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
    def CREW_VISION_MODEL(self):
        return self._format_model(self.GROQ_VISION_MODEL)

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()