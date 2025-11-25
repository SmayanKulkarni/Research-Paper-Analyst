from typing import List, Dict, Any, Optional

import asyncio
import httpx
from bs4 import BeautifulSoup

from app.utils.logging import logger
from app.services.embeddings import embed_texts
from app.services.parquet_store import append_new_papers
from app.services.pinecone_client import upsert_vectors


ARXIV_API = "https://export.arxiv.org/api/query"


def _extract_from_arxiv_xml(xml_data: str) -> List[Dict[str, Any]]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(xml_data, "xml")
    entries = soup.find_all("entry")
    raw_papers: List[Dict[str, Any]] = []
    for e in entries:
        try:
            raw_papers.append(
                {
                    "title": e.title.text.strip(),
                    "summary": e.summary.text.strip(),
                    "url": e.id.text.strip(),
                }
            )
        except Exception:
            continue
    return raw_papers


def _fetch_arxiv_xml(query: str, max_raw_results: int, attempts: int = 3) -> Optional[str]:
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_raw_results,
    }

    backoff = 1
    with httpx.Client(timeout=30) as client:
        for attempt in range(1, attempts + 1):
            try:
                r = client.get(ARXIV_API, params=params)
                r.raise_for_status()
                return r.text
            except httpx.HTTPStatusError as e:
                status = e.response.status_code if e.response is not None else None
                msg = f"arXiv HTTP error (status={status}) on attempt {attempt}: {e}"
                logger.warning(msg)
                if status == 429 and attempt < attempts:
                    asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                raise
            except Exception as e:
                logger.warning(f"arXiv fetch attempt {attempt} failed: {e}")
                if attempt < attempts:
                    asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                raise


def _try_arxiv_package(query: str, max_results: int) -> List[Dict[str, Any]]:
    """Use the `arxiv` Python package to search arXiv for papers.

    Defensive: if the package isn't installed or the call fails, return an empty list.
    Returns items mapped to {title, summary, url}.
    """
    try:
        import arxiv
    except Exception:
        return []

    try:
        search = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance)
        results: List[Dict[str, Any]] = []
        for r in search.results():
            try:
                title = r.title
                summary = r.summary
                pdf_url = r.pdf_url if hasattr(r, 'pdf_url') else ''
                entry_url = r.entry_id if hasattr(r, 'entry_id') else getattr(r, 'id', '')
                meta = {"title": title, "summary": summary, "url": pdf_url or entry_url}
                results.append(meta)
            except Exception:
                continue
        return results
    except Exception as e:
        logger.debug(f"arxiv package search failed: {e}")
        return []


def crawl_and_ingest(query: str, max_raw_results: int = 25, max_papers: int = 5) -> List[Dict[str, Any]]:
    """Crawl arXiv for `query` using the arxiv package when available, falling back to the
    arXiv XML API if needed. Compute embeddings and upsert up to `max_papers` new papers.

    This function intentionally uses only arXiv as the source of papers.
    """
    # Prefer the arxiv package client
    raw_papers = _try_arxiv_package(query, max_raw_results)

    # Fallback to XML if package not available or returned no results
    if not raw_papers:
        try:
            xml_data = _fetch_arxiv_xml(query, max_raw_results)
            if xml_data:
                raw_papers = _extract_from_arxiv_xml(xml_data)
        except Exception as e:
            logger.warning(f"arXiv fallback (xml) failed: {e}")

    if not raw_papers:
        logger.info("Crawler found 0 arXiv papers.")
        return []

    # embed summaries (local model) and attach embeddings
    summaries = [p.get("summary", "") for p in raw_papers]
    embeddings = embed_texts(summaries)

    for p, emb in zip(raw_papers, embeddings):
        p["embedding"] = emb

    # Persist (append) to parquet; append_new_papers should return only truly new papers
    new_papers = append_new_papers(raw_papers)
    if not new_papers:
        logger.info("No new papers to add to the store.")
        return []

    # limit how many we upsert for this run to avoid over-ingesting
    limited_papers = new_papers[:max_papers]

    vectors = []
    for p in limited_papers:
        vectors.append(
            {
                "id": p["paper_id"],
                "values": p["embedding"],
                "metadata": {
                    "title": p["title"],
                    "url": p.get("url", ""),
                    "text": p.get("summary", ""),
                },
            }
        )

    upsert_vectors(vectors)

    logger.info(f"Added {len(limited_papers)} papers to Pinecone (requested up to {max_papers})")
    return limited_papers


def crawl_and_ingest_sync(query: str, max_raw_results: int = 25, max_papers: int = 5) -> List[Dict[str, Any]]:
    """Synchronous wrapper around the crawler. Uses asyncio.run to execute the async flow."""
    return crawl_and_ingest(query, max_raw_results=max_raw_results, max_papers=max_papers)
from typing import List, Dict, Any, Optional

import asyncio
import httpx
import os
from bs4 import BeautifulSoup

from app.utils.logging import logger
from app.services.embeddings import embed_texts
from app.services.parquet_store import append_new_papers
from app.services.pinecone_client import upsert_vectors


ARXIV_API = "https://export.arxiv.org/api/query"


async def _fetch_arxiv_xml(query: str, max_raw_results: int, attempts: int = 3) -> Optional[str]:
    """Existing arXiv XML fetch (used as a robust fallback)."""
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_raw_results,
    }

    backoff = 1
    async with httpx.AsyncClient(timeout=30) as client:
        for attempt in range(1, attempts + 1):
            try:
                r = await client.get(ARXIV_API, params=params)
                r.raise_for_status()
                return r.text
            except httpx.HTTPStatusError as e:
                status = e.response.status_code if e.response is not None else None
                msg = f"arXiv HTTP error (status={status}) on attempt {attempt}: {e}"
                logger.warning(msg)
                if status == 429 and attempt < attempts:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                raise
            except Exception as e:
                logger.warning(f"arXiv fetch attempt {attempt} failed: {e}")
                if attempt < attempts:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                raise


def _extract_from_arxiv_xml(xml_data: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(xml_data, "xml")
    entries = soup.find_all("entry")
    raw_papers: List[Dict[str, Any]] = []
    for e in entries:
        try:
            raw_papers.append(
                {
                    "title": e.title.text.strip(),
                    "summary": e.summary.text.strip(),
                    "url": e.id.text.strip(),
                }
            )
        except Exception:
            continue
    return raw_papers


def _try_crewai_search(query: str, max_results: int) -> List[Dict[str, Any]]:
    """Attempt to use CrewAI's scraping utilities if available.

    This function is defensive: it will try several common CrewAI APIs and return
    a list of {title, summary, url} dicts on success, otherwise an empty list.
    """
    try:
        import crewai
    except Exception:
        return []

    results: List[Dict[str, Any]] = []
    # Try a few plausible CrewAI client patterns (defensive)
    try:
        # pattern 1: crewai.Scraper
        Scraper = getattr(crewai, "Scraper", None)
        if Scraper:
            s = Scraper()
            if hasattr(s, "search"):
                items = s.search(query, limit=max_results)
            elif hasattr(s, "run"):
                items = s.run(query, limit=max_results)
            else:
                items = []
            for it in items or []:
                # accept flexible shapes
                title = getattr(it, "title", None) or it.get("title") if isinstance(it, dict) else None
                summary = getattr(it, "summary", None) or it.get("summary") if isinstance(it, dict) else None
                url = getattr(it, "url", None) or it.get("url") if isinstance(it, dict) else None
                if title and (summary or url):
                    results.append({"title": title, "summary": summary or "", "url": url or ""})
            if results:
                return results

        # pattern 2: crewai.client.Client()
        Client = getattr(crewai, "Client", None)
        if Client:
            c = Client()
            if hasattr(c, "search"):
                items = c.search(query, limit=max_results)
                for it in items or []:
                    if isinstance(it, dict):
                        results.append({"title": it.get("title", ""), "summary": it.get("summary", ""), "url": it.get("url", "")})
                if results:
                    return results
    except Exception as e:
        logger.debug(f"CrewAI search attempt failed: {e}")

    return []


def _try_crawl4ai_search(query: str, max_results: int) -> List[Dict[str, Any]]:
    """Try using crawl4ai (if available) to find papers/pages.

    This is defensive: if the package or API isn't available, return an empty list.
    Maps results to {title, summary, url}.
    """
    try:
        # attempt to import common client modules/names
        try:
            import crawl4ai
            client_cls = getattr(crawl4ai, "Client", None) or getattr(crawl4ai, "Crawl4AIClient", None)
        except Exception:
            # try alternate package name
            import crawl4ai_client as c4
            client_cls = getattr(c4, "Client", None)
            crawl4ai = c4
    except Exception:
        return []

    try:
        api_key = os.getenv("CRAWL4AI_API_KEY")
        client = client_cls(api_key=api_key) if client_cls is not None else None
        if client is None:
            # try top-level helper
            if hasattr(crawl4ai, "search"):
                items = crawl4ai.search(query, limit=max_results)
            else:
                return []
        else:
            # common method names: search/scrape/query
            if hasattr(client, "search"):
                items = client.search(query, limit=max_results)
            elif hasattr(client, "scrape"):
                items = client.scrape(query, limit=max_results)
            else:
                # fallback to a generic run interface
                items = client.run(query, limit=max_results) if hasattr(client, "run") else []

        results: List[Dict[str, Any]] = []
        for it in (items or [])[:max_results]:
            # accept dict-like or object-like items
            if isinstance(it, dict):
                title = it.get("title") or it.get("name")
                summary = it.get("summary") or it.get("snippet") or it.get("description") or ""
                url = it.get("url") or it.get("link") or it.get("href") or ""
            else:
                title = getattr(it, "title", None) or getattr(it, "name", None)
                summary = getattr(it, "summary", None) or getattr(it, "snippet", None) or ""
                url = getattr(it, "url", None) or getattr(it, "link", None) or ""
            if title and (summary or url):
                results.append({"title": title, "summary": summary, "url": url})
        return results
    except Exception as e:
        logger.debug(f"crawl4ai search attempt failed: {e}")
        return []


def _scrape_url_with_crawl4ai(client, url: str) -> Optional[Dict[str, Any]]:
    """Ask crawl4ai client to scrape a specific URL and return a {title, summary, url} dict.

    This function is defensive: it tries common method names and falls back to None on failure.
    """
    try:
        # common method names: scrape_url, scrape, fetch, fetch_url
        if hasattr(client, "scrape_url"):
            out = client.scrape_url(url)
        elif hasattr(client, "scrape"):
            out = client.scrape(url)
        elif hasattr(client, "fetch"):
            out = client.fetch(url)
        elif hasattr(client, "fetch_url"):
            out = client.fetch_url(url)
        else:
            # no suitable method
            return None

        # normalize output
        if out is None:
            return None
        if isinstance(out, dict):
            title = out.get("title") or out.get("name")
            summary = out.get("summary") or out.get("text") or out.get("snippet") or ""
            return {"title": title or url, "summary": summary, "url": url}
        # if object-like
        title = getattr(out, "title", None) or getattr(out, "name", None) or url
        summary = getattr(out, "summary", None) or getattr(out, "text", None) or getattr(out, "snippet", None) or ""
        return {"title": title, "summary": summary, "url": url}
    except Exception as e:
        logger.debug(f"crawl4ai failed to scrape url {url}: {e}")
        return None


def _assist_crawl4ai_with_ddg(query: str, max_results: int, client) -> List[Dict[str, Any]]:
    """When crawl4ai search yields nothing, help it by finding candidate URLs via DuckDuckGo
    and asking crawl4ai to scrape them. Falls back to direct fetching if crawl4ai scrape methods
    aren't available.
    """
    candidates = _try_ddg_search(query + " site:pdf OR filetype:pdf OR site:arxiv.org", max_results * 3)
    results: List[Dict[str, Any]] = []
    tried = set()
    for c in candidates:
        url = c.get("url")
        if not url or url in tried:
            continue
        tried.add(url)
        # prefer direct pdf links
        if url.lower().endswith(".pdf"):
            # try to fetch metadata (title) by HEAD request or simple filename
            try:
                # ask crawl4ai to scrape PDF if possible; ONLY accept results that crawl4ai can scrape
                scraped = None
                if client is not None:
                    scraped = _scrape_url_with_crawl4ai(client, url)
                if scraped:
                    results.append(scraped)
                    if len(results) >= max_results:
                        break
                # otherwise skip (do not perform direct fetch)
            except Exception:
                continue
        else:
            # non-pdf candidate; try scrape
            try:
                scraped = None
                if client is not None:
                    scraped = _scrape_url_with_crawl4ai(client, url)
                if scraped:
                    results.append(scraped)
                # do NOT fallback to direct fetch; only accept crawl4ai-scrapable pages
                if len(results) >= max_results:
                    break
            except Exception:
                continue
    return results


def _try_ddg_search(query: str, max_results: int) -> List[Dict[str, Any]]:
    """Use DuckDuckGo (duckduckgo_search) as a free search fallback.

    This is defensive: if the package isn't installed or the call fails, return an empty list.
    Returns items as dicts with title/summary/url.
    """
    try:
        from duckduckgo_search import ddg
    except Exception:
        return []

    try:
        items = ddg(query, max_results=max_results)
        results: List[Dict[str, Any]] = []
        for it in (items or [])[:max_results]:
            # ddg returns dicts with keys like 'title', 'body', 'href'
            title = it.get("title")
            snippet = it.get("body") or it.get("snippet") or ""
            link = it.get("href") or it.get("url") or ""
            if title and (snippet or link):
                results.append({"title": title, "summary": snippet, "url": link})
        return results
    except Exception as e:
        logger.debug(f"DuckDuckGo search attempt failed: {e}")
        return []


def _try_arxiv_package(query: str, max_results: int) -> List[Dict[str, Any]]:
    """Use the `arxiv` Python package to search arXiv for papers.

    Defensive: if the package isn't installed or the call fails, return an empty list.
    Returns items mapped to {title, summary, url} (pdf url included in summary metadata where available).
    """
    try:
        import arxiv
    except Exception:
        return []

    try:
        search = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance)
        results: List[Dict[str, Any]] = []
        for r in search.results():
            try:
                title = r.title
                summary = r.summary
                pdf_url = r.pdf_url if hasattr(r, 'pdf_url') else ''
                entry_url = r.entry_id if hasattr(r, 'entry_id') else getattr(r, 'id', '')
                # Prefer pdf_url in metadata
                meta = {"title": title, "summary": summary, "url": pdf_url or entry_url}
                results.append(meta)
            except Exception:
                continue
        return results
    except Exception as e:
        logger.debug(f"arxiv package search failed: {e}")
        return []


async def crawl_and_ingest(query: str, max_raw_results: int = 25, max_papers: int = 5) -> List[Dict[str, Any]]:
    """Crawl using multiple strategies (CrewAI, Serper, arXiv fallback) and ingest new papers.

    Strategy order:
    1. CrewAI scraping (if available)
    2. Serper (if available and API key present)
    3. arXiv API (existing fallback)
    """
    # 1) Try CrewAI scraping in a thread to avoid blocking the async loop
    raw_papers: List[Dict[str, Any]] = []
    try:
        raw_papers = await asyncio.to_thread(_try_crewai_search, query, max_raw_results)
        if raw_papers:
            logger.info(f"Found {len(raw_papers)} results via CrewAI scraping")
    except Exception as e:
        logger.debug(f"CrewAI scraping raised: {e}")

    # 2) If no results, try Serper
    if not raw_papers:
        try:
            raw_papers = await asyncio.to_thread(_try_ddg_search, query, max_raw_results)
            if raw_papers:
                logger.info(f"Found {len(raw_papers)} results via DuckDuckGo (ddg)")
        except Exception as e:
            logger.debug(f"DuckDuckGo scraping raised: {e}")

    # 3) Fallback to arXiv
    if not raw_papers:
        try:
            xml_data = await _fetch_arxiv_xml(query, max_raw_results)
            if xml_data:
                raw_papers = _extract_from_arxiv_xml(xml_data)
                logger.info(f"Found {len(raw_papers)} results via arXiv fallback")
        except Exception as e:
            logger.warning(f"arXiv fallback failed: {e}")

    if not raw_papers:
        logger.info("Crawler found 0 papers.")
        return []

    # embed summaries (local model) and attach embeddings
    summaries = [p.get("summary", "") for p in raw_papers]
    embeddings = embed_texts(summaries)

    for p, emb in zip(raw_papers, embeddings):
        p["embedding"] = emb

    # Persist (append) to parquet; append_new_papers should return only truly new papers
    new_papers = append_new_papers(raw_papers)
    if not new_papers:
        logger.info("No new papers to add to the store.")
        return []

    # limit how many we upsert for this run to avoid over-ingesting
    limited_papers = new_papers[:max_papers]

    vectors = []
    for p in limited_papers:
        vectors.append(
            {
                "id": p["paper_id"],
                "values": p["embedding"],
                "metadata": {
                    "title": p["title"],
                    "url": p.get("url", ""),
                    "text": p.get("summary", ""),
                },
            }
        )

    upsert_vectors(vectors)

    logger.info(f"Added {len(limited_papers)} papers to Pinecone (requested up to {max_papers})")
    return limited_papers


def crawl_and_ingest_sync(query: str, max_raw_results: int = 25, max_papers: int = 5) -> List[Dict[str, Any]]:
    """Synchronous wrapper around the async crawler. Uses asyncio.run to execute the async flow."""
    import asyncio

    return asyncio.run(crawl_and_ingest(query, max_raw_results=max_raw_results, max_papers=max_papers))
