from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.crew.orchestrator import run_full_analysis
from app.models.schemas import AnalysisResult
from app.utils.logging import logger

router = APIRouter(prefix="/api", tags=["analyze"])


@router.post("/analyze/", response_model=AnalysisResult)
async def analyze(file_id: str):
    try:
        result = run_full_analysis(file_id=file_id)
    except Exception as e:
        logger.exception("Analysis failed")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    # result is a dict with "raw" or structured content; for now wrap into AnalysisResult
    # we treat result["raw"] as a big combined text and put into proofreading
    if isinstance(result, dict) and "raw" in result:
        combined = result["raw"]
        return JSONResponse(
            content=AnalysisResult(
                proofreading=combined,
                structure="(See combined analysis)",
                citations="(See combined analysis)",
                consistency="(See combined analysis)",
                vision=None,
                plagiarism=None,
            ).dict()
        )

    # if you later structure your crew outputs into sections, map them here
    return JSONResponse(
        content=AnalysisResult(
            proofreading=str(result),
            structure="(Not yet split)",
            citations="(Not yet split)",
            consistency="(Not yet split)",
            vision=None,
            plagiarism=None,
        ).dict()
    )
