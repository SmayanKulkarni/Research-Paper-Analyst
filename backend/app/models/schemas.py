from typing import Optional, List
from pydantic import BaseModel


class UploadResponse(BaseModel):
    file_id: str
    filename: str


class PlagiarismMatch(BaseModel):
    source_id: str
    source_title: Optional[str] = None
    source_url: Optional[str] = None
    similarity: float
    source_excerpt: str
    user_excerpt: str
    source_type: Optional[str] = None  # "indexed" or "arxiv_discovered"


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
    plagiarism: Optional[List[PlagiarismMatch]] = None
