import os
import pymupdf4llm
from typing import Dict, Any
from app.utils.logging import logger

def parse_pdf_to_markdown(file_path: str) -> Dict[str, Any]:
    """
    Parses a PDF into Layout-Aware Markdown using PyMuPDF4LLM.
    
    Why this is better:
    - Preserves Headers (H1, H2) structure.
    - Converts Tables into Markdown format (readable by LLMs).
    - Keeps bold/italic emphasis.
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return {"text": "", "images": []}

    logger.info(f"Parsing PDF with Layout Awareness: {file_path}")
    
    try:
        # 1. Convert to Markdown
        # This function handles the complex layout analysis internally
        md_text = pymupdf4llm.to_markdown(file_path)
        
        # 2. Basic Metadata extraction (optional, can be expanded)
        # We rely on the markdown structure itself for content
        
        logger.info(f"Successfully converted PDF to {len(md_text)} chars of Markdown.")
        
        return {
            "text": md_text,
            "images": [] # pymupdf4llm can extract image bytes, simplified here
        }
        
    except Exception as e:
        logger.error(f"Layout parsing failed: {e}")
        # Fallback to empty or error message
        return {"text": "", "images": []}