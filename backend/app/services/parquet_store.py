import os
import json
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

    # Define columns, now including sparse_values for hybrid search backup
    columns = ["paper_id", "title", "summary", "url", "embedding", "sparse_values"]

    if os.path.exists(parquet_path):
        try:
            df_existing = pd.read_parquet(parquet_path)
            # Ensure backward compatibility if old parquet didn't have sparse_values
            if "sparse_values" not in df_existing.columns:
                df_existing["sparse_values"] = None
        except Exception:
            df_existing = pd.DataFrame(columns=columns)
    else:
        df_existing = pd.DataFrame(columns=columns)

    existing_urls = set(df_existing["url"].tolist()) if not df_existing.empty else set()

    records = []
    for p in raw_papers:
        # Debug log to verify keys being passed
        # logger.info(f"Processing paper '{p.get('title')}'. Keys present: {list(p.keys())}")

        if p["url"] in existing_urls:
            continue
            
        # Handle sparse values serialization (it's usually a dict like {'indices': [], 'values': []})
        # Default to None if missing, or use empty dict string if you prefer non-null
        sparse_val = p.get("sparse_values")
        
        if sparse_val:
             # logger.info(f"Sparse values found for {p.get('title')}: {str(sparse_val)[:50]}...")
             sparse_val_str = json.dumps(sparse_val)
        else:
             # Fallback: Log a warning if expected data is missing for new records
             # logger.warning(f"No sparse_values found for {p.get('title')}")
             sparse_val_str = None

        records.append(
            {
                "paper_id": str(uuid.uuid4()),
                "title": p["title"],
                "summary": p["summary"],
                "url": p["url"],
                "embedding": p["embedding"],
                "sparse_values": sparse_val_str
            }
        )

    if not records:
        logger.info("No new papers to append to parquet.")
        return []

    df_new = pd.DataFrame(records)
    # Ensure columns match before concat to avoid issues
    for col in columns:
        if col not in df_new.columns:
            df_new[col] = None
            
    df_all = pd.concat([df_existing, df_new], ignore_index=True)

    df_all.to_parquet(parquet_path, index=False)
    logger.info(f"Parquet updated at {parquet_path} with {len(records)} new papers.")

    return records