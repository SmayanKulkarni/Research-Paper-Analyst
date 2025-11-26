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

    # Parse CrewAI output into structured analysis sections
    # CrewAI returns task outputs keyed by agent type
    proofreading_output = None
    structure_output = None
    citations_output = None
    consistency_output = None
    plagiarism_output = None
    vision_output = None

    if isinstance(result, dict):
        # Extract outputs from crew result keys
        for key, value in result.items():
            if isinstance(value, str):
                # Match key names to agent tasks
                if "proofreading" in key.lower() or "proof" in key.lower():
                    proofreading_output = value
                elif "structure" in key.lower():
                    structure_output = value
                elif "citation" in key.lower():
                    citations_output = value
                elif "consistency" in key.lower():
                    consistency_output = value
                elif "plagiarism" in key.lower():
                    plagiarism_output = value
                elif "vision" in key.lower():
                    vision_output = value

    # Fallback: if crew.kickoff() returns a raw string, parse it
    if not proofreading_output and isinstance(result, dict):
        if "raw" in result:
            proofreading_output = result["raw"]
    
    if not proofreading_output:
        proofreading_output = str(result)

    return JSONResponse(
        content=AnalysisResult(
            proofreading=proofreading_output or "No proofreading analysis available",
            structure=structure_output or "No structure analysis available",
            citations=citations_output or "No citation analysis available",
            consistency=consistency_output or "No consistency analysis available",
            vision=vision_output,
            plagiarism=plagiarism_output,
        ).dict()
    )
