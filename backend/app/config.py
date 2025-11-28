from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    PROJECT_NAME: str = "Research Paper Analyzer"

    # ============================
    # GROQ (LLM Provider)
    # ============================
    GROQ_API_KEY: str = Field(..., env="GROQ_API_KEY")
    
    # UNLIMITED MODE: Using Llama 3.3 70B Versatile for all agents.
    GROQ_CITATION_MODEL: str = Field("groq/llama-3.3-70b-versatile", env="GROQ_CITATION_MODEL")
    GROQ_STRUCTURE_MODEL: str = Field("groq/llama-3.3-70b-versatile", env="GROQ_STRUCTURE_MODEL")
    
    # Consistency Model
    GROQ_CONSISTENCY_MODEL: str = Field("groq/openai/gpt-oss-20b", env="GROQ_CONSISTENCY_MODEL")
    
    GROQ_PLAGIARISM_MODEL: str = Field("groq/llama-3.3-70b-versatile", env="GROQ_PLAGIARISM_MODEL")
    GROQ_PROOFREADER_MODEL: str = Field("groq/llama-3.3-70b-versatile", env="GROQ_PROOFREADER_MODEL")
    GROQ_VISION_MODEL: str = Field("groq/llama-3.2-11b-vision-preview", env="GROQ_VISION_MODEL")

    OPENAI_API_KEY: Optional[str] = Field(None, env="OPENAI_API_KEY")

    # ============================
    # PINECONE & SEARCH
    # ============================
    PINECONE_API_KEY: str = Field(..., env="PINECONE_API_KEY")
    PINECONE_ENVIRONMENT: str = Field(..., env="PINECONE_ENVIRONMENT")
    PINECONE_INDEX_NAME: str = Field("research-plagiarism", env="PINECONE_INDEX_NAME")
    
    # REMOVED: Cross-Encoder config
    
    # ============================
    # EMBEDDINGS
    # ============================
    # Using 'all-mpnet-base-v2' (State-of-the-art open source).
    EMBEDDING_MODEL_NAME: str = Field("sentence-transformers/all-mpnet-base-v2", env="EMBEDDING_MODEL_NAME")
    EMBEDDING_DIM: int = Field(768, env="EMBEDDING_DIM")

    # ============================
    # PROCESSING CONFIG
    # ============================
    PLAGIARISM_CHUNK_SIZE: int = Field(500, env="PLAGIARISM_CHUNK_SIZE")
    PLAGIARISM_CHUNK_OVERLAP: int = Field(100, env="PLAGIARISM_CHUNK_OVERLAP")

    # ============================
    # LOCAL STORAGE
    # ============================
    STORAGE_ROOT: str = Field("storage", env="STORAGE_ROOT")
    UPLOADS_DIR: str = Field("uploads", env="UPLOADS_DIR")
    PARQUET_LOCAL_ROOT: str = Field("storage/parquet_data", env="PARQUET_LOCAL_ROOT")
    
    # FAISS Index Storage
    FAISS_INDEX_PATH: str = Field("storage/faiss_index", env="FAISS_INDEX_PATH")

    def _format_model(self, model: str) -> str:
        """Ensure model string is formatted for CrewAI (groq/model-name)"""
        if model.startswith("groq/"):
            return model
        return f"groq/{model}"

    @property
    def CREW_CITATION_MODEL(self): return self._format_model(self.GROQ_CITATION_MODEL)
    @property
    def CREW_STRUCTURE_MODEL(self): return self._format_model(self.GROQ_STRUCTURE_MODEL)
    @property
    def CREW_CONSISTENCY_MODEL(self): return self._format_model(self.GROQ_CONSISTENCY_MODEL)
    @property
    def CREW_PLAGIARISM_MODEL(self): return self._format_model(self.GROQ_PLAGIARISM_MODEL)
    @property
    def CREW_PROOFREADER_MODEL(self): return self._format_model(self.GROQ_PROOFREADER_MODEL)
    @property
    def CREW_VISION_MODEL(self): return self._format_model(self.GROQ_VISION_MODEL)

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()