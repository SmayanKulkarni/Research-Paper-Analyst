import os
import uuid
from typing import Dict, List

import fitz  # PyMuPDF
from app.config import get_settings
from app.utils.logging import logger

settings = get_settings()


def parse_pdf_to_text_and_images(file_path: str) -> Dict[str, List[str]]:
    """
    Extract full text and save page images from a PDF.
    Returns dict: { "text": str, "images": [image_paths] }
    """
    storage_root = settings.STORAGE_ROOT
    images_dir = os.path.join(storage_root, settings.IMAGES_DIR)
    os.makedirs(images_dir, exist_ok=True)

    doc = fitz.open(file_path)

    all_text_parts: List[str] = []
    image_paths: List[str] = []

    base_id = os.path.splitext(os.path.basename(file_path))[0] + "_" + str(uuid.uuid4())[:8]

    for page_index in range(len(doc)):
        page = doc[page_index]
        text = page.get_text("text")
        if text:
            all_text_parts.append(text)

        # render page to PNG image (for vision / OCR)
        pix = page.get_pixmap()
        image_path = os.path.join(images_dir, f"{base_id}_page{page_index+1}.png")
        pix.save(image_path)
        image_paths.append(image_path)

    full_text = "\n\n".join(all_text_parts)
    logger.info(f"Parsed PDF {file_path}: {len(all_text_parts)} text chunks, {len(image_paths)} images")

    return {"text": full_text, "images": image_paths}
