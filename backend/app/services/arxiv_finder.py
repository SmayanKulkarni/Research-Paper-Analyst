"""
arxiv_finder.py

Resolve citation arXiv IDs/URLs to actual paper metadata and ingest them into the vector store.
Uses the arxiv Python package and tools module as fallback.
"""

from typing import List, Dict, Any, Optional
import re
from app.utils.logging import logger
from app.services.embeddings import embed_texts
from app.services.parquet_store import append_new_papers
from app.services.pinecone_client import upsert_vectors


def _extract_arxiv_id_from_url(url: str) -> Optional[str]:
    """Extract arXiv ID from a URL.
    
    Matches:
    - https://arxiv.org/abs/2101.12345
    - https://arxiv.org/pdf/2101.12345.pdf
    - https://arxiv.org/abs/2101.12345v2
    """
    match = re.search(r'/(?:abs|pdf)/(\d{4}\.\d{4,5})', url)
    if match:
        arxiv_id = match.group(1)
        # Remove version suffix if present (v1, v2, etc.)
        arxiv_id = re.sub(r'v\d+$', '', arxiv_id)
        return arxiv_id
    return None


def fetch_arxiv_paper_by_id(arxiv_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch paper metadata from arXiv by ID using the arxiv Python package.
    
    Returns a dict with: title, summary, url, authors, published (date).
    Returns None if fetch fails or package unavailable.
    """
    try:
        import arxiv
    except ImportError:
        logger.warning("arxiv package not installed; cannot fetch paper by ID")
        return None
    
    try:
        # arxiv.Search expects a query; use ID directly
        search = arxiv.Search(query=arxiv_id, max_results=1)
        for result in search.results():
            # Map arxiv result to our schema
            return {
                "title": result.title,
                "summary": result.summary,
                "url": result.pdf_url or result.entry_id,
                "authors": ", ".join([a.name for a in result.authors]) if result.authors else None,
                "published": str(result.published)[:10] if result.published else None,
            }
        return None
    except Exception as e:
        logger.debug(f"Failed to fetch arXiv paper {arxiv_id}: {e}")
        return None


def fetch_arxiv_paper_by_url(url: str) -> Optional[Dict[str, Any]]:
    """
    Fetch paper metadata from arXiv using a URL.
    Extracts the arxiv ID from the URL and fetches via ID.
    """
    arxiv_id = _extract_arxiv_id_from_url(url)
    if not arxiv_id:
        logger.warning(f"Could not extract arXiv ID from URL: {url}")
        return None
    
    return fetch_arxiv_paper_by_id(arxiv_id)


def resolve_citation_to_arxiv(citation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Resolve a citation dict (from citation_extractor) to a full arXiv paper.
    
    Tries in order:
    1. Direct arXiv ID lookup
    2. URL-based lookup (arXiv or DOI URLs)
    3. DOI search (search arXiv by DOI if present)
    4. Title/authors search (if available)
    
    Returns paper dict or None.
    """
    # Try direct arxiv_id first
    if citation.get("arxiv_id"):
        paper = fetch_arxiv_paper_by_id(citation["arxiv_id"])
        if paper:
            return paper
    
    # Try URL-based lookup
    if citation.get("url"):
        paper = fetch_arxiv_paper_by_url(citation["url"])
        if paper:
            return paper
    
    # Try DOI search - search arXiv for papers matching the DOI
    # (Some papers are on both arXiv and DOI registries)
    if citation.get("doi"):
        try:
            import arxiv
            doi = citation["doi"]
            # Search for the DOI in arXiv (some papers include DOI in their metadata)
            search = arxiv.Search(query=f"doi:{doi}", max_results=1, sort_by=arxiv.SortCriterion.Relevance)
            for result in search.results():
                logger.debug(f"Found arXiv paper via DOI {doi}: {result.title}")
                return {
                    "title": result.title,
                    "summary": result.summary,
                    "url": result.pdf_url or result.entry_id,
                    "authors": ", ".join([a.name for a in result.authors]) if result.authors else None,
                    "published": str(result.published)[:10] if result.published else None,
                }
        except Exception as e:
            logger.debug(f"DOI search failed for {citation.get('doi')}: {e}")
    
    # Try title + authors search (last resort)
    # This is a more expensive operation, so we do it last
    title = citation.get("title")
    authors = citation.get("authors")
    
    if title:
        try:
            import arxiv
            # Build a simple query from title
            query = f"title:{title}"
            search = arxiv.Search(query=query, max_results=1, sort_by=arxiv.SortCriterion.Relevance)
            for result in search.results():
                return {
                    "title": result.title,
                    "summary": result.summary,
                    "url": result.pdf_url or result.entry_id,
                    "authors": ", ".join([a.name for a in result.authors]) if result.authors else None,
                    "published": str(result.published)[:10] if result.published else None,
                }
        except Exception as e:
            logger.debug(f"Title-based arXiv search failed for '{title}': {e}")
    
    return None


def ingest_arxiv_papers_from_citations(
    citations: List[Dict[str, Any]],
    max_papers: int = 5,
) -> List[Dict[str, Any]]:
    """
    Resolve citations to arXiv papers, compute embeddings, and ingest into vector store.
    
    Returns list of successfully ingested papers.
    """
    resolved_papers: List[Dict[str, Any]] = []
    
    for citation in citations:
        paper = resolve_citation_to_arxiv(citation)
        if paper:
            resolved_papers.append(paper)
            if len(resolved_papers) >= max_papers:
                break
    
    if not resolved_papers:
        logger.info("No arXiv papers resolved from citations")
        return []
    
    # Embed summaries
    summaries = [p.get("summary", "") for p in resolved_papers]
    embeddings = embed_texts(summaries)
    
    for p, emb in zip(resolved_papers, embeddings):
        p["embedding"] = emb
    
    # Append to parquet (deduplicates by URL)
    new_papers = append_new_papers(resolved_papers)
    if not new_papers:
        logger.info("All resolved papers already exist in store")
        return []
    
    # Upsert to Pinecone
    vectors = []
    for p in new_papers:
        vectors.append({
            "id": p["paper_id"],
            "values": p["embedding"],
            "metadata": {
                "title": p["title"],
                "url": p.get("url", ""),
                "text": p.get("summary", ""),
                "authors": p.get("authors"),
                "published": p.get("published"),
            },
        })
    
    upsert_vectors(vectors)
    logger.info(f"Ingested {len(new_papers)} arXiv papers from citations into Pinecone")
    
    return new_papers
