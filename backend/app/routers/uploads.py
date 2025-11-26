import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool

from app.config import get_settings
from app.models.schemas import UploadResponse
from app.services.pdf_parser import parse_pdf_to_text_and_images
from app.services.paper_discovery import find_related_papers_to_abstract
from app.services.embeddings import embed_texts
from app.services.parquet_store import append_new_papers
from app.services.pinecone_client import upsert_vectors
from app.utils.logging import logger


settings = get_settings()
router = APIRouter(prefix="/api/uploads", tags=["uploads"])


async def _ingest_related_papers_via_discovery(abstract: str, file_id: str, category: str = "cs.CL", top_k: int = 10):
    """
    Background task: Use embedding-based discovery to find and ingest related papers.
    
    This uses the get_papers.py pipeline:
    1. Embed the uploaded paper abstract
    2. Search arXiv for similar papers in category
    3. Embed candidate abstracts
    4. Compute similarity, get top-K
    5. Ingest into vector store (Pinecone + Parquet)
    
    This replaces the old citation-based ingestion method with semantic discovery.
    """
    if not abstract or len(abstract.strip()) < 50:
        logger.info(f"Abstract too short or empty for {file_id}, skipping discovery ingestion")
        return
    
    try:
        logger.info(f"Starting embedding-based paper discovery for {file_id} (category: {category}, top_k: {top_k})")
        
        # Use paper discovery to find related papers
        discovered_papers = await run_in_threadpool(
            find_related_papers_to_abstract,
            abstract,
            category,
            top_k
        )
        
        if not discovered_papers:
            logger.info(f"No related papers discovered for {file_id}")
            return
        
        logger.info(f"Discovered {len(discovered_papers)} related papers for {file_id}")
        
        # Embed paper summaries
        summaries = [p.get("summary", "") for p in discovered_papers]
        embeddings = await run_in_threadpool(embed_texts, summaries)
        
        # Attach embeddings to papers
        for p, emb in zip(discovered_papers, embeddings):
            p["embedding"] = emb
        
        # Append to parquet (deduplicates by URL)
        new_papers = await run_in_threadpool(append_new_papers, discovered_papers)
        
        if not new_papers:
            logger.info(f"All discovered papers already exist in store for {file_id}")
            return
        
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
                    "source": "discovered",  # Mark as discovered via embedding similarity
                },
            })
        
        await run_in_threadpool(upsert_vectors, vectors)
        logger.info(f"Successfully ingested {len(new_papers)} discovered papers into Pinecone for {file_id}")
        
    except Exception as e:
        logger.exception(f"Paper discovery ingestion failed for {file_id}: {e}")


@router.post("/", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    storage_root = settings.STORAGE_ROOT
    uploads_dir = os.path.join(storage_root, settings.UPLOADS_DIR)
    os.makedirs(uploads_dir, exist_ok=True)

    file_id = str(uuid.uuid4())
    dest_path = os.path.join(uploads_dir, f"{file_id}.pdf")
    content = await file.read()
    with open(dest_path, "wb") as f:
        f.write(content)

    # Schedule background paper discovery and ingestion (non-blocking)
    # Uses embedding-based discovery (get_papers.py pipeline) instead of citation-based ingestion
    if background_tasks is not None:
        try:
            parsed = parse_pdf_to_text_and_images(dest_path)
            abstract = parsed.get("text", "")[:1000]  # Use first 1000 chars as abstract
            background_tasks.add_task(_ingest_related_papers_via_discovery, abstract, file_id, category="cs.CL", top_k=10)
        except Exception as e:
            logger.warning(f"Could not extract abstract for discovery ingestion: {e}")

    return JSONResponse(
        content=UploadResponse(file_id=file_id, filename="paper.pdf").dict()
    )