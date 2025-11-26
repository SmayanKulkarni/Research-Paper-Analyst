from typing import Dict, List, Any

import fitz  # PyMuPDF
from app.config import get_settings
from app.utils.logging import logger

settings = get_settings()


def parse_pdf_to_text_and_images(file_path: str) -> Dict[str, Any]:
    """
    Extract full text from a PDF.
    
    Returns dict: { "text": str, "images": [] }
    """
    doc = fitz.open(file_path)

    all_text_parts: List[str] = []
    image_paths: List[str] = []  # Empty - image extraction disabled

    for page_index in range(len(doc)):
        page = doc[page_index]
        text = page.get_text("text")
        if text:
            all_text_parts.append(text)

    full_text = "\n\n".join(all_text_parts)
    logger.info(f"Parsed PDF {file_path}: {len(all_text_parts)} text chunks")

    return {"text": full_text, "images": image_paths}
