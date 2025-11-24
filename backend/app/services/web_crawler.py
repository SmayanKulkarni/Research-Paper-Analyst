from typing import List, Dict, Any

import httpx
from bs4 import BeautifulSoup

from app.utils.logging import logger
from app.services.embeddings import embed_texts
from app.services.parquet_store import append_new_papers
from app.services.pinecone_client import upsert_vectors

ARXIV_API = "http://export.arxiv.org/api/query"


async def crawl_and_ingest(query: str, max_raw_results: int = 25) -> List[Dict[str, Any]]:
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_raw_results,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(ARXIV_API, params=params)
        r.raise_for_status()
        xml_data = r.text

    soup = BeautifulSoup(xml_data, "xml")
    entries = soup.find_all("entry")

    raw_papers: List[Dict[str, Any]] = []
    for e in entries:
        raw_papers.append(
            {
                "title": e.title.text.strip(),
                "summary": e.summary.text.strip(),
                "url": e.id.text.strip(),
            }
        )

    if not raw_papers:
        logger.info("Crawler found 0 papers.")
        return []

    summaries = [p["summary"] for p in raw_papers]
    embeddings = embed_texts(summaries)

    for p, emb in zip(raw_papers, embeddings):
        p["embedding"] = emb

    new_papers = append_new_papers(raw_papers)

    if not new_papers:
        return []

    vectors = []
    for p in new_papers:
        vectors.append(
            {
                "id": p["paper_id"],
                "values": p["embedding"],
                "metadata": {
                    "title": p["title"],
                    "url": p["url"],
                    "text": p["summary"],
                },
            }
        )

    upsert_vectors(vectors)

    logger.info(f"Added {len(new_papers)} papers to Pinecone")
    return new_papers
