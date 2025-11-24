from typing import List, Dict, Any

from pinecone import Pinecone, ServerlessSpec

from app.config import get_settings
from app.utils.logging import logger

settings = get_settings()

pc = Pinecone(api_key=settings.PINECONE_API_KEY)

existing = [i["name"] for i in pc.list_indexes()]

if settings.PINECONE_INDEX_NAME not in existing:
    logger.info(f"Creating Pinecone index: {settings.PINECONE_INDEX_NAME}")
    pc.create_index(
        name=settings.PINECONE_INDEX_NAME,
        dimension=settings.EMBEDDING_DIM,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region=settings.PINECONE_ENVIRONMENT,
        ),
    )

index = pc.Index(settings.PINECONE_INDEX_NAME)


def upsert_vectors(vectors: List[Dict[str, Any]]) -> None:
    index.upsert(vectors=vectors)


def query_similar(vector: list, top_k: int = 5, filter: Dict[str, Any] | None = None):
    res = index.query(
        vector=vector,
        top_k=top_k,
        include_metadata=True,
        filter=filter,
    )
    return res.matches or []
