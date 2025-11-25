from typing import List

from app.services.embeddings import embed_texts
from app.services.pinecone_client import query_similar
from app.models.schemas import PlagiarismMatch
from app.utils.logging import logger
from app.services.web_crawler import crawl_and_ingest_sync
from app.services.llm_provider import call_groq_with_retries, groq_llm


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
    fallback_to_crawl: bool = False,
    max_papers_to_crawl: int = 5,
    use_groq_for_query: bool = False,
) -> List[PlagiarismMatch]:
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


    # unreachable normally


def check_plagiarism_with_fallback(
    text: str,
    max_matches_per_chunk: int = 3,
    similarity_threshold: float = 0.85,
    fallback_to_crawl: bool = True,
    max_papers_to_crawl: int = 5,
    use_groq_for_query: bool = False,
) -> List[PlagiarismMatch]:
    """Run the normal plagiarism check and optionally fallback to crawling arXiv for similar papers

    - If no matches are found and fallback_to_crawl is True, the function will attempt to crawl
      for similar papers (up to `max_papers_to_crawl`) and re-run the query against Pinecone.
    - If use_groq_for_query is True, the function will attempt to produce a compact query using the
      groq LLM. If that fails it falls back to a simple text snippet.
    """
    # First try the normal path
    results = check_plagiarism(text, max_matches_per_chunk, similarity_threshold)
    if results:
        return results

    if not fallback_to_crawl:
        return results

    # Build a query for crawling
    query = text.strip().replace("\n", " ")[:800]
    if use_groq_for_query:
        try:
            prompt = (
                "Extract a concise search query (3-7 words or a short phrase) that best represents the topic of the following academic text:\n\n"
                + text[:2000]
            )
            resp = call_groq_with_retries(groq_llm.__call__, prompt)
            # ChatGroq returns structured response in different shapes; try to coerce to string
            if isinstance(resp, str):
                query = resp.strip()[:800]
            else:
                # attempt to extract text-like content
                query = str(resp)[:800]
        except Exception:
            logger.warning("Groq query extraction failed; falling back to text snippet.")

    # Run synchronous crawler to populate Pinecone
    try:
        added = crawl_and_ingest_sync(query, max_raw_results=25, max_papers=max_papers_to_crawl)
        logger.info(f"Fallback crawl added {len(added)} papers to store")
    except Exception as e:
        logger.exception(f"Fallback crawl failed: {e}")
        return results

    # Re-run plagiarism check after crawl
    return check_plagiarism(text, max_matches_per_chunk, similarity_threshold)
