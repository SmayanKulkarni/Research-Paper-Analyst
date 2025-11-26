from typing import List

from app.services.embeddings import embed_texts
from app.services.pinecone_client import query_similar
from app.models.schemas import PlagiarismMatch
from app.utils.logging import logger

# Optional: Use embedding-based paper discovery as fallback
try:
    from app.services.paper_discovery import find_related_papers_to_abstract
    DISCOVERY_AVAILABLE = True
except ImportError:
    DISCOVERY_AVAILABLE = False


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


def check_plagiarism_with_discovery(
    text: str,
    max_matches_per_chunk: int = 3,
    similarity_threshold: float = 0.85,
    enable_discovery: bool = True,
    discovery_top_k: int = 5,
) -> List[PlagiarismMatch]:
    """Check plagiarism with optional embedding-based paper discovery fallback.
    
    Pipeline:
    1. Check Pinecone for indexed papers (citations + uploaded PDFs)
    2. If no matches found and enable_discovery=True:
       - Use embedding similarity to find related arXiv papers
       - Add these as candidate sources for plagiarism
    
    Args:
        text: Text to check
        max_matches_per_chunk: Max matches per chunk
        similarity_threshold: Min similarity score
        enable_discovery: Whether to use paper discovery fallback
        discovery_top_k: Max papers to discover as fallback
    
    Returns:
        List of PlagiarismMatch results
    """
    # First try the normal Pinecone path
    results = check_plagiarism(text, max_matches_per_chunk, similarity_threshold)
    if results:
        logger.info(f"Found {len(results)} plagiarism matches in Pinecone")
        return results

    # Fallback: Use embedding-based discovery to find related papers
    if enable_discovery and DISCOVERY_AVAILABLE:
        logger.info("No Pinecone matches found; using embedding-based discovery for related papers...")
        try:
            # Find related papers by abstract similarity
            related_papers = find_related_papers_to_abstract(
                abstract=text[:500],  # Use first 500 chars as abstract proxy
                category="cs.CL",  # Default to NLP category
                top_k=discovery_top_k,
                max_candidates=100,
            )
            
            if related_papers:
                logger.info(f"Discovery found {len(related_papers)} potentially related papers")
                
                # Convert discovered papers to plagiarism matches
                for paper in related_papers:
                    results.append(
                        PlagiarismMatch(
                            source_id=paper.get("arxiv_id", paper.get("entry_id")),
                            source_title=paper.get("title"),
                            source_url=paper.get("pdf_url"),
                            similarity=paper.get("similarity_score", 0.5),  # Use embedding similarity
                            source_excerpt=paper.get("abstract", "")[:200],
                            user_excerpt=text[:200],
                            source_type="arxiv_discovered",  # Mark as discovered
                        )
                    )
                
                logger.info(f"Added {len(related_papers)} discovered papers as potential sources")
        except Exception as e:
            logger.debug(f"Discovery fallback failed: {e}; returning Pinecone results only")
    else:
        logger.info("No matches found; discovery fallback not available")
    
    return results
