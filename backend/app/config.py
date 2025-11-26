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
    
    # Agent-specific models to distribute load across different Groq models
    # This avoids rate limiting by using different TPM pools for each agent
    # Format: groq/<model_name> for CrewAI/litellm integration
    GROQ_CITATION_MODEL: str = Field("groq/llama-3.1-8b-instant", env="GROQ_CITATION_MODEL")
    GROQ_STRUCTURE_MODEL: str = Field("groq/llama-3.3-70b-versatile", env="GROQ_STRUCTURE_MODEL")
    GROQ_CONSISTENCY_MODEL: str = Field("groq/qwen/qwen3-32b", env="GROQ_CONSISTENCY_MODEL")
    GROQ_PLAGIARISM_MODEL: str = Field("groq/llama-3.3-70b-versatile", env="GROQ_PLAGIARISM_MODEL")
    GROQ_PROOFREADER_MODEL: str = Field("groq/llama-3.3-70b-versatile", env="GROQ_PROOFREADER_MODEL")
    GROQ_VISION_MODEL: str = Field("groq/llama-3.2-11b-vision-preview", env="GROQ_VISION_MODEL")

    # Make OpenAI Key Optional to avoid validation errors if empty
    OPENAI_API_KEY: Optional[str] = Field(None, env="OPENAI_API_KEY")

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
    # LOCAL STORAGE
    # ============================
    STORAGE_ROOT: str = Field("storage", env="STORAGE_ROOT")
    UPLOADS_DIR: str = Field("uploads", env="UPLOADS_DIR")

    def _format_model(self, model: str) -> str:
        """Ensure model string is formatted for CrewAI (groq/model-name)"""
        if model.startswith("groq/"):
            return model
        return f"groq/{model}"

    @property
    def CREW_CITATION_MODEL(self):
        """Returns citation agent model formatted for CrewAI"""
        return self._format_model(self.GROQ_CITATION_MODEL)

    @property
    def CREW_STRUCTURE_MODEL(self):
        """Returns structure agent model formatted for CrewAI"""
        return self._format_model(self.GROQ_STRUCTURE_MODEL)

    @property
    def CREW_CONSISTENCY_MODEL(self):
        """Returns consistency agent model formatted for CrewAI"""
        return self._format_model(self.GROQ_CONSISTENCY_MODEL)

    @property
    def CREW_PLAGIARISM_MODEL(self):
        """Returns plagiarism agent model formatted for CrewAI"""
        return self._format_model(self.GROQ_PLAGIARISM_MODEL)

    @property
    def CREW_PROOFREADER_MODEL(self):
        """Returns proofreader agent model formatted for CrewAI"""
        return self._format_model(self.GROQ_PROOFREADER_MODEL)

    @property
    def CREW_VISION_MODEL(self):
        """Returns vision agent model formatted for CrewAI"""
        return self._format_model(self.GROQ_VISION_MODEL)

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()