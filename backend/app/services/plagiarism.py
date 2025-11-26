from typing import List

from app.services.embeddings import embed_texts
from app.services.pinecone_client import query_similar
from app.models.schemas import PlagiarismMatch
from app.utils.logging import logger


def chunk_text(text: str, max_len: int = 800) -> List[str]:
    chunks: List[str] = []
    current: List[str] = []
    n = 0

    for line in text.splitlines():
        line = line.strip("\n")
        if not line:
            continue

        if n + len(line) > max_len and current:
            chunks.append("\n".join(current))
            current = [line]
            n = len(line)
        else:
            current.append(line)
            n += len(line)

    if current:
        chunks.append("\n".join(current))

    return [c for c in chunks if c.strip()]


def check_plagiarism(
    text: str,
    max_matches_per_chunk: int = 3,
    similarity_threshold: float = 0.85,
) -> List[PlagiarismMatch]:
    """Check text against indexed papers in Pinecone.
    
    Uses local vector similarity search against papers in the vector store.
    
    Args:
        text: Text to check for plagiarism
        max_matches_per_chunk: Max matches to return per text chunk
        similarity_threshold: Minimum similarity score to include (0-1)
    
    Returns:
        List of PlagiarismMatch results
    """
    chunks = chunk_text(text)
    logger.info(f"Checking plagiarism on {len(chunks)} text chunks")

    vectors = embed_texts(chunks)
    results: List[PlagiarismMatch] = []

    for chunk, vector in zip(chunks, vectors):
        matches = query_similar(vector, top_k=max_matches_per_chunk)

        for m in matches:
            if (m.score or 0.0) < similarity_threshold:
                continue

            meta = m.metadata or {}

            results.append(
                PlagiarismMatch(
                    source_id=m.id,
                    source_title=meta.get("title"),
                    source_url=meta.get("url"),
                    similarity=m.score,
                    source_excerpt=meta.get("text", ""),
                    user_excerpt=chunk,
                )
            )

    return results
