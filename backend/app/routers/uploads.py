import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool

from app.config import get_settings
from app.models.schemas import UploadResponse
from app.services.pdf_parser import parse_pdf_to_text_and_images
from app.services.arxiv_finder import ingest_arxiv_papers_from_citations
from app.utils.logging import logger


settings = get_settings()
router = APIRouter(prefix="/api/uploads", tags=["uploads"])


async def _process_citations_on_upload(dest_path: str, file_id: str, max_papers: int = 5):
    """
    Background task: parse uploaded PDF, extract citations, resolve to arXiv papers,
    and ingest them into the vector store.
    
    Handles case where no citations found gracefully.
    """
    try:
        parsed = await run_in_threadpool(parse_pdf_to_text_and_images, dest_path)
        citations = parsed.get("citations", [])
        
        if not citations:
            logger.info(f"No arXiv-linkable citations found in {file_id}")
            return
        
        logger.info(f"Processing {len(citations)} citations from {file_id}")
        
        # Resolve citations to arXiv papers and ingest
        ingested = await run_in_threadpool(
            ingest_arxiv_papers_from_citations,
            citations,
            max_papers
        )
        
        logger.info(f"Successfully ingested {len(ingested)} arXiv papers from citations in {file_id}")
        
    except Exception as e:
        # Don't fail the upload on citation processing errors; log and continue
        logger.exception(f"Citation processing failed for {file_id}: {e}")


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

    # Schedule background citation extraction and paper ingestion (non-blocking)
    if background_tasks is not None:
        background_tasks.add_task(_process_citations_on_upload, dest_path, file_id, max_papers=5)

    return JSONResponse(
        content=UploadResponse(file_id=file_id, filename="paper.pdf").dict()
    )

