from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    PROJECT_NAME: str = "Research Paper Analyzer"

    # ============================
    # GROQ
    # ============================
    GROQ_API_KEY: str = Field(..., env="GROQ_API_KEY")
    
    # Raw model names from .env
    # Default text model (lighter, lower TPM usage). Can be overridden via .env
    GROQ_TEXT_MODEL: str = Field("groq/llama-3.1-8b-instant", env="GROQ_TEXT_MODEL")
    GROQ_VISION_MODEL: str = Field("llama-4-scout-17b-16e-instruct", env="GROQ_VISION_MODEL")
    GROQ_COMPRESSION_MODEL: str = Field("llama-3-8b-8192", env="GROQ_COMPRESSION_MODEL")  # Smaller for efficiency

    # Make OpenAI Key Optional to avoid validation errors if empty
    OPENAI_API_KEY: Optional[str] = Field(None, env="OPENAI_API_KEY")

    # ============================
    # STORAGE MODE SWITCH
    # ============================
    USE_LOCAL_STORAGE: bool = Field(True, env="USE_LOCAL_STORAGE")
    PARQUET_LOCAL_ROOT: str = Field("storage/parquet", env="PARQUET_LOCAL_ROOT")

    # ============================
    # PINECONE
    # ============================
    PINECONE_API_KEY: str = Field(..., env="PINECONE_API_KEY")
    PINECONE_ENVIRONMENT: str = Field(..., env="PINECONE_ENVIRONMENT")
    PINECONE_INDEX_NAME: str = Field("research-plagiarism", env="PINECONE_INDEX_NAME")

    # ============================
    # EMBEDDINGS (local)
    # ============================
    EMBEDDING_MODEL_NAME: str = Field("BAAI/bge-large-en", env="EMBEDDING_MODEL_NAME")
    EMBEDDING_DIM: int = Field(1024, env="EMBEDDING_DIM")

    # ============================
    # AZURE BLOB (ONLY WHEN USE_LOCAL_STORAGE=false)
    # ============================
    AZURE_STORAGE_ACCOUNT_NAME: str = Field("localdev", env="AZURE_STORAGE_ACCOUNT_NAME")
    AZURE_STORAGE_ACCOUNT_KEY: str = Field("localdev", env="AZURE_STORAGE_ACCOUNT_KEY")
    AZURE_BLOB_CONTAINER: str = Field("localdev", env="AZURE_BLOB_CONTAINER")
    PARQUET_OBJECT_PATH: str = Field("papers.parquet", env="PARQUET_OBJECT_PATH")

    # ============================
    # LOCAL TEMP STORAGE
    # ============================
    STORAGE_ROOT: str = Field("storage", env="STORAGE_ROOT")
    UPLOADS_DIR: str = Field("uploads", env="UPLOADS_DIR")
    IMAGES_DIR: str = Field("images", env="IMAGES_DIR")

    # ============================
    # TOKEN OPTIMIZATION (NEW)
    # ============================
    GROQ_TPM_LIMIT: int = Field(6000, env="GROQ_TPM_LIMIT")  # Free tier actual limit (was 8000, reducing to actual)
    TOKEN_BUDGET_SAFETY_MARGIN: float = Field(0.70, env="TOKEN_BUDGET_SAFETY_MARGIN")  # Use up to 70% before degradation (was 80%)
    MAX_CHUNKS_TO_COMPRESS: int = Field(5, env="MAX_CHUNKS_TO_COMPRESS")  # Reduced from 10 to 5
    MAX_ANALYSIS_TEXT_LENGTH: int = Field(3000, env="MAX_ANALYSIS_TEXT_LENGTH")  # Reduced from 5000 to 3000 chars
    # Concurrency controls for LLM calls in this process (reduce TPM bursts)
    CREW_MAX_CONCURRENT_LLM_CALLS: int = Field(1, env="CREW_MAX_CONCURRENT_LLM_CALLS")  # Reduced from 2 to 1 (sequential)

    @property
    def CREW_TEXT_MODEL(self):
        """Returns the model string formatted for CrewAI (groq/model-name)"""
        if self.GROQ_TEXT_MODEL.startswith("groq/"):
            return self.GROQ_TEXT_MODEL
        return f"groq/{self.GROQ_TEXT_MODEL}"

    @property
    def CREW_VISION_MODEL(self):
        """Returns the vision model string formatted for CrewAI"""
        if self.GROQ_VISION_MODEL.startswith("groq/"):
            return self.GROQ_VISION_MODEL
        return f"groq/{self.GROQ_VISION_MODEL}"

    @property
    def CREW_COMPRESSION_MODEL(self):
        """Returns the compression model string formatted for CrewAI"""
        if self.GROQ_COMPRESSION_MODEL.startswith("groq/"):
            return self.GROQ_COMPRESSION_MODEL
        return f"groq/{self.GROQ_COMPRESSION_MODEL}"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()