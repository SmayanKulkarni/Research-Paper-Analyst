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
    GROQ_PROOFREADER_MODEL: str = Field("groq/llama-3.1-8b-instant", env="GROQ_PROOFREADER_MODEL")
    GROQ_MATH_MODEL: str = Field("groq/llama-3.1-8b-instant", env="GROQ_MATH_MODEL")
    GROQ_CLARITY_MODEL: str = Field("groq/llama-3.1-8b-instant", env="GROQ_CLARITY_MODEL")  # Clarity of thought agent
    GROQ_FLOW_MODEL: str = Field("groq/llama-3.1-8b-instant", env="GROQ_FLOW_MODEL")  # Flow analysis agent

    # Make OpenAI Key Optional
    OPENAI_API_KEY: Optional[str] = Field(None, env="OPENAI_API_KEY")

    # ============================
    # PINECONE & SEARCH
    # ============================
    PINECONE_API_KEY: str = Field(..., env="PINECONE_API_KEY")
    PINECONE_ENVIRONMENT: str = Field(..., env="PINECONE_ENVIRONMENT")
    PINECONE_INDEX_NAME: str = Field("research-papers", env="PINECONE_INDEX_NAME")
    
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
    CHUNK_SIZE: int = Field(512, env="CHUNK_SIZE")  # For paper discovery and embeddings
    CHUNK_OVERLAP: int = Field(50, env="CHUNK_OVERLAP")

    # ============================
    # DYNAMIC TOKEN BUDGET (Accuracy-First Approach)
    # Tokens are calculated based on actual PDF content length.
    # EXPANDED budget: 500k+ tokens for comprehensive analysis.
    # 
    # Strategy: Each agent gets tokens proportional to its task complexity:
    # - Language Quality: Full paper text needed for thorough grammar/style review
    # - Structure: Full paper for section analysis
    # - Citation: Full paper to find and verify all citations
    # - Clarity: Full paper for logical reasoning analysis
    # - Flow: Full paper for narrative and transition analysis
    # - Math Review: Only math sections (variable)
    # - Vision: Based on number/complexity of images
    # - Report: Aggregation of all outputs
    # 
    # PREPROCESSING: Multi-point sampling strategy (beginning, middle, end sections)
    # ============================
    
    # Maximum token budget (expanded for longer/complex papers - no artificial ceiling)
    MAX_TOKEN_BUDGET: int = Field(500000, env="MAX_TOKEN_BUDGET")
    
    # Minimum tokens per agent (ensures quality even for short papers)
    MIN_TOKENS_PER_AGENT: int = Field(8000, env="MIN_TOKENS_PER_AGENT")
    
    # Output token limits - very generous for detailed analysis
    MAX_COMPLETION_TOKENS: int = Field(6000, env="MAX_COMPLETION_TOKENS")
    
    # Vision-specific settings
    MAX_VISION_TOKENS: int = Field(3000, env="MAX_VISION_TOKENS")
    MAX_IMAGES_TO_ANALYZE: int = Field(25, env="MAX_IMAGES_TO_ANALYZE")
    
    # Token estimation ratio (characters to tokens, roughly 4 chars = 1 token)
    CHARS_PER_TOKEN: int = Field(4, env="CHARS_PER_TOKEN")
    
    # ============================
    # PREPROCESSING SAMPLING STRATEGY
    # ============================
    # Enables multi-point sampling from different parts of the document
    ENABLE_MULTI_POINT_SAMPLING: bool = Field(True, env="ENABLE_MULTI_POINT_SAMPLING")
    
    # Number of samples to extract from each section (beginning, middle, end)
    SAMPLING_POINTS_PER_SECTION: int = Field(3, env="SAMPLING_POINTS_PER_SECTION")
    
    # Maximum characters per extracted sample (before truncation)
    MAX_SAMPLE_LENGTH: int = Field(15000, env="MAX_SAMPLE_LENGTH")
    
    # Enable full-text analysis for short papers (< this many chars)
    SHORT_PAPER_THRESHOLD: int = Field(20000, env="SHORT_PAPER_THRESHOLD")

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
    def CREW_PROOFREADER_MODEL(self):
        return self._format_model(self.GROQ_PROOFREADER_MODEL)

    @property
    def CREW_CLARITY_MODEL(self):
        return self._format_model(self.GROQ_CLARITY_MODEL)

    @property
    def CREW_FLOW_MODEL(self):
        return self._format_model(self.GROQ_FLOW_MODEL)

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