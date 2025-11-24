import os
from typing import List, Dict, Any
import uuid

import pandas as pd
from app.config import get_settings
from app.utils.logging import logger

settings = get_settings()


def _get_parquet_path() -> str:
    root = settings.PARQUET_LOCAL_ROOT
    os.makedirs(root, exist_ok=True)
    return os.path.join(root, "papers.parquet")


def append_new_papers(raw_papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Append new papers to a local parquet file, deduplicating by URL.
    Returns only the new records added (each with paper_id).
    """
    parquet_path = _get_parquet_path()

    if os.path.exists(parquet_path):
        df_existing = pd.read_parquet(parquet_path)
    else:
        df_existing = pd.DataFrame(columns=["paper_id", "title", "summary", "url", "embedding"])

    existing_urls = set(df_existing["url"].tolist()) if not df_existing.empty else set()

    records = []
    for p in raw_papers:
        if p["url"] in existing_urls:
            continue
        records.append(
            {
                "paper_id": str(uuid.uuid4()),
                "title": p["title"],
                "summary": p["summary"],
                "url": p["url"],
                "embedding": p["embedding"],
            }
        )

    if not records:
        logger.info("No new papers to append to parquet.")
        return []

    df_new = pd.DataFrame(records)
    df_all = pd.concat([df_existing, df_new], ignore_index=True)

    df_all.to_parquet(parquet_path, index=False)
    logger.info(f"Parquet updated at {parquet_path} with {len(records)} new papers.")

    return records
