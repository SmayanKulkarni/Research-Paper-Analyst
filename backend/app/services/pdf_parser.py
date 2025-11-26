import os
import uuid
from typing import Dict, List, Any

import fitz  # PyMuPDF
from app.config import get_settings
from app.utils.logging import logger
from app.services.citation_extractor import extract_citations_from_text, filter_arxiv_citations

settings = get_settings()


def parse_pdf_to_text_and_images(file_path: str, extract_citations: bool = True) -> Dict[str, Any]:
    """
    Extract full text and optionally extract citations from a PDF.
    
    Image extraction is currently disabled (not used in the pipeline).
    
    Returns dict: { "text": str, "images": [], "citations": [...] }
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
    logger.info(f"Parsed PDF {file_path}: {len(all_text_parts)} text chunks (image extraction disabled)")

    result: Dict[str, Any] = {"text": full_text, "images": image_paths, "citations": []}
    
    # Extract citations if requested
    if extract_citations:
        try:
            all_citations = extract_citations_from_text(full_text, max_citations=50)
            arxiv_citations = filter_arxiv_citations(all_citations)
            result["citations"] = arxiv_citations
            logger.info(f"Extracted {len(arxiv_citations)} arXiv-linkable citations from PDF")
        except Exception as e:
            logger.warning(f"Citation extraction failed: {e}")

    return result
