import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.models.schemas import UploadResponse
from app.utils.logging import logger

settings = get_settings()
router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.post("/", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF file for analysis.
    
    Returns a file_id that can be used with the /api/analyze/ endpoint.
    """
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
    
    logger.info(f"Uploaded PDF {file.filename} with file_id={file_id}")

    return JSONResponse(
        content=UploadResponse(file_id=file_id, filename="paper.pdf").dict()
    )