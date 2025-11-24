from typing import List
import pytesseract
from PIL import Image

from app.services.llm_provider import vision_llm
from app.models.schemas import VisionFigureAnalysis
from app.utils.logging import logger


def analyze_images(image_paths: List[str]) -> List[VisionFigureAnalysis]:
    """
    Basic vision pipeline:
    - OCR images using Tesseract
    - Ask Groq vision model to interpret tables/figures based on OCR text
    """
    results: List[VisionFigureAnalysis] = []

    for path in image_paths:
        try:
            img = Image.open(path)
            ocr_text = pytesseract.image_to_string(img)
        except Exception as e:
            logger.error(f"OCR failed for {path}: {e}")
            ocr_text = ""

        prompt = (
            "You are an expert in reading scientific tables, charts, and figures.\n"
            "Given the following OCR text extracted from a figure or table in a research paper, "
            "identify what the figure is about, what variables or metrics it shows, whether it's "
            "clear and properly labeled, and suggest any improvements.\n\n"
            f"OCR TEXT:\n{ocr_text}\n\n"
            "Now provide a concise analysis."
        )

        try:
            analysis = vision_llm.predict(prompt)
        except Exception as e:
            logger.error(f"Vision LLM failed for {path}: {e}")
            analysis = "Vision analysis failed."

        results.append(
            VisionFigureAnalysis(
                image_path=path,
                ocr_text=ocr_text,
                analysis=analysis,
            )
        )

    return results
