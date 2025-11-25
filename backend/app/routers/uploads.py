import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool

from app.config import get_settings
from app.models.schemas import UploadResponse
from app.services.pdf_parser import parse_pdf_to_text_and_images
from app.services.web_crawler import crawl_and_ingest


settings = get_settings()
router = APIRouter(prefix="/api/uploads", tags=["uploads"])


async def _crawl_on_upload(dest_path: str, file_id: str, max_papers: int = 5):
    """Background task: parse uploaded PDF, craft a short query and crawl arXiv for similar papers."""
    try:
        parsed = await run_in_threadpool(parse_pdf_to_text_and_images, dest_path)
        text = parsed.get("text", "") if isinstance(parsed, dict) else ""

        # Build a compact query: prefer the abstract (if present), else first 400 chars
        q = ""
        lower = text.lower()
        if "abstract" in lower:
            # try to find the abstract block
            idx = lower.find("abstract")
            snippet = text[idx : idx + 1200]
            q = snippet.strip().replace("\n", " ")[:800]
        else:
            q = text.strip().replace("\n", " ")[:800]

        if not q:
            q = file_id

        # run the crawler: limit to max_papers (default 5)
        await crawl_and_ingest(q, max_raw_results=25, max_papers=max_papers)
    except Exception as e:
        # don't fail the upload on crawl errors; log and continue
        from app.utils.logging import logger

        logger.exception(f"Background crawl failed for {dest_path}: {e}")



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

    # schedule background crawl/ingest for similar papers (non-blocking)
    if background_tasks is not None:
        background_tasks.add_task(_crawl_on_upload, dest_path, file_id, 5)

    return JSONResponse(
        content=UploadResponse(file_id=file_id, filename="paper.pdf").dict()
    )
