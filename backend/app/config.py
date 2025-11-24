from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    PROJECT_NAME: str = "Research Paper Analyzer"

    # ============================
    # GROQ
    # ============================
    # CrewAI's Groq native provider will read GROQ_API_KEY from the environment.
    GROQ_API_KEY: str = Field(..., env="GROQ_API_KEY")
    # This is the *CrewAI* model string, not raw Groq:
    GROQ_MODEL_NAME: str = Field(
        "groq/llama3-70b-8192",  # as per CrewAI + StackOverflow answer
        env="GROQ_MODEL_NAME",
    )
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")

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
    # EMBEDDINGS (local, no OpenAI)
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

    class Config:
        env_file = ".env"
        case_sensitive = True
        # Ignore random env vars like CREWAI_DISABLE_OPENAI instead of raising.
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
