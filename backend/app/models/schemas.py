from typing import Optional, List
from pydantic import BaseModel


class UploadResponse(BaseModel):
    file_id: str
    filename: str


class VisionFigureAnalysis(BaseModel):
    image_path: str
    ocr_text: str
    analysis: str


class AnalysisResult(BaseModel):
    proofreading: str
    structure: str
    citations: str
    consistency: str
    vision: Optional[List[VisionFigureAnalysis]] = None
    pdf_report_path: Optional[str] = None
