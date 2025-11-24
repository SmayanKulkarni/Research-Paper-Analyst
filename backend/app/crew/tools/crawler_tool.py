from typing import Any

import asyncio
from crewai.tools import tool

from app.services.web_crawler import crawl_and_ingest


@tool("Smart Academic Crawler")
def crawler_tool(query: str) -> Any:
    """
    Crawl arXiv for recent research papers related to the query, compute embeddings,
    deduplicate, persist them in local parquet storage, and upsert vectors into Pinecone.

    Returns a list of newly added paper metadata records.
    """
    return asyncio.run(crawl_and_ingest(query))
