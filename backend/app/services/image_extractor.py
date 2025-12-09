"""
Image Extraction Service for PDFs.

Extracts images from PDF files and filters to keep only the most significant ones
(top N by file size) to avoid analyzing irrelevant small icons, logos, etc.
"""

import os
import fitz  # PyMuPDF
from typing import List, Tuple
from pathlib import Path

from app.config import get_settings
from app.utils.logging import logger

settings = get_settings()

# Minimum image dimensions to consider (filters out tiny icons)
MIN_IMAGE_WIDTH = 100
MIN_IMAGE_HEIGHT = 100

# Supported image formats for vision models
SUPPORTED_FORMATS = {"png", "jpeg", "jpg", "webp", "gif"}


def extract_images_from_pdf(
    pdf_path: str,
    output_dir: str = None,
    max_images: int = None,
    min_width: int = MIN_IMAGE_WIDTH,
    min_height: int = MIN_IMAGE_HEIGHT,
) -> List[str]:
    """
    Extract images from a PDF and save the top N largest ones.
    
    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save extracted images (default: storage/images/<pdf_name>/)
        max_images: Maximum number of images to keep (default from config)
        min_width: Minimum image width to consider
        min_height: Minimum image height to consider
    
    Returns:
        List of paths to the extracted images (sorted by size, largest first)
    """
    if max_images is None:
        max_images = settings.MAX_IMAGES_TO_ANALYZE
    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found: {pdf_path}")
        return []
    
    # Setup output directory
    pdf_name = Path(pdf_path).stem
    if output_dir is None:
        output_dir = os.path.join(settings.STORAGE_ROOT, "images", pdf_name)
    
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"Extracting images from PDF: {pdf_path}")
    
    extracted_images: List[Tuple[str, int]] = []  # (path, size_bytes)
    
    try:
        doc = fitz.open(pdf_path)
        image_count = 0
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images(full=True)
            
            for img_index, img_info in enumerate(image_list):
                xref = img_info[0]
                
                try:
                    # Extract the image
                    base_image = doc.extract_image(xref)
                    
                    if not base_image:
                        continue
                    
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"].lower()
                    width = base_image.get("width", 0)
                    height = base_image.get("height", 0)
                    
                    # Filter by dimensions
                    if width < min_width or height < min_height:
                        logger.debug(f"Skipping small image: {width}x{height}")
                        continue
                    
                    # Filter by supported formats
                    if image_ext not in SUPPORTED_FORMATS:
                        # Try to save as PNG if format not supported
                        image_ext = "png"
                    
                    # Save the image
                    image_filename = f"page{page_num + 1}_img{img_index + 1}.{image_ext}"
                    image_path = os.path.join(output_dir, image_filename)
                    
                    with open(image_path, "wb") as f:
                        f.write(image_bytes)
                    
                    file_size = len(image_bytes)
                    extracted_images.append((image_path, file_size))
                    image_count += 1
                    
                    logger.debug(f"Extracted: {image_filename} ({width}x{height}, {file_size} bytes)")
                    
                except Exception as e:
                    logger.debug(f"Failed to extract image {xref} from page {page_num + 1}: {e}")
                    continue
        
        doc.close()
        logger.info(f"Extracted {image_count} images from PDF")
        
    except Exception as e:
        logger.error(f"Failed to process PDF for images: {e}")
        return []
    
    # Sort by file size (largest first) and keep top N
    extracted_images.sort(key=lambda x: x[1], reverse=True)
    top_images = extracted_images[:max_images]
    
    # Clean up images that didn't make the cut
    kept_paths = {img[0] for img in top_images}
    for img_path, _ in extracted_images:
        if img_path not in kept_paths:
            try:
                os.remove(img_path)
            except Exception:
                pass
    
    result_paths = [img[0] for img in top_images]
    
    if result_paths:
        logger.info(f"Keeping top {len(result_paths)} images by file size:")
        for i, (path, size) in enumerate(top_images):
            logger.info(f"  {i+1}. {os.path.basename(path)} - {size / 1024:.1f} KB")
    else:
        logger.info("No significant images found in PDF")
    
    return result_paths


def cleanup_extracted_images(pdf_path: str) -> None:
    """
    Clean up extracted images for a specific PDF.
    
    Args:
        pdf_path: Path to the original PDF file
    """
    pdf_name = Path(pdf_path).stem
    output_dir = os.path.join(settings.STORAGE_ROOT, "images", pdf_name)
    
    if os.path.exists(output_dir):
        import shutil
        shutil.rmtree(output_dir)
        logger.info(f"Cleaned up images directory: {output_dir}")
