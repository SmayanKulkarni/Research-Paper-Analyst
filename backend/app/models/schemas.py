from typing import Optional, List, Any
from pydantic import BaseModel


class UploadResponse(BaseModel):
    file_id: str
    filename: str


class VisionFigureAnalysis(BaseModel):
    image_path: str
    ocr_text: str
    analysis: str


class AnalysisResult(BaseModel):
    """Analysis results from all agents."""
    language_quality: Optional[str] = None
    structure: Optional[str] = None
    citations: Optional[str] = None
    math_review: Optional[str] = None
    plagiarism: Optional[str] = None
    vision: Optional[str] = None
    final_report: Optional[str] = None
    pdf_report_path: Optional[str] = None
