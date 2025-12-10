import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, FileResponse

from app.crew.orchestrator import run_full_analysis
from app.models.schemas import AnalysisResult
from app.services.pdf_report_generator import PDFReportGenerator
from app.utils.logging import logger

router = APIRouter(prefix="/api", tags=["analyze"])


@router.post("/analyze/", response_model=AnalysisResult)
async def analyze(file_id: str):
    try:
        result = run_full_analysis(file_id=file_id)
    except Exception as e:
        logger.exception("Analysis failed")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    # Extract results directly from orchestrator output
    if not isinstance(result, dict):
        raise HTTPException(status_code=500, detail="Analysis did not return expected format")
    
    return JSONResponse(
        content=AnalysisResult(
            language_quality=result.get("language_quality"),
            structure=result.get("structure"),
            citations=result.get("citations"),
            math_review=result.get("math_review"),
            plagiarism=result.get("plagiarism"),
            vision=result.get("vision"),
            final_report=result.get("final_report"),
            pdf_report_path=result.get("pdf_report_path"),
        ).dict()
    )


@router.get("/report/{file_id}")
async def get_report_pdf(file_id: str):
    """
    Download the PDF analysis report for a specific file.
    """
    reports_dir = "storage/reports"
    
    if not os.path.exists(reports_dir):
        raise HTTPException(status_code=404, detail="Reports directory not found")
    
    matching_files = [
        f for f in os.listdir(reports_dir) 
        if f.startswith(f"analysis_report_{file_id}") and f.endswith(".pdf")
    ]
    
    if not matching_files:
        raise HTTPException(
            status_code=404, 
            detail=f"No PDF report found for file_id: {file_id}. Run analysis first."
        )
    
    latest_report = sorted(matching_files)[-1]
    pdf_path = os.path.join(reports_dir, latest_report)
    
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF report file not found")
    
    return FileResponse(
        path=pdf_path,
        filename=latest_report,
        media_type="application/pdf"
    )


@router.post("/report/generate/{file_id}")
async def generate_report_pdf(file_id: str):
    """
    Generate a new PDF report from existing analysis results.
    """
    try:
        result = run_full_analysis(file_id=file_id)
        
        if not isinstance(result, dict):
            raise HTTPException(status_code=500, detail="Analysis did not return expected format")
        
        pdf_path = result.get("pdf_report_path")
        
        if pdf_path and os.path.exists(pdf_path):
            return JSONResponse(content={
                "success": True,
                "pdf_path": pdf_path,
                "message": "PDF report generated successfully"
            })
        else:
            pdf_generator = PDFReportGenerator()
            pdf_path = pdf_generator.generate_report(result, file_id)
            
            return JSONResponse(content={
                "success": True,
                "pdf_path": pdf_path,
                "message": "PDF report generated successfully"
            })
            
    except Exception as e:
        logger.exception("PDF report generation failed")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")
