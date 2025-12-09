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

    # Parse CrewAI output into structured analysis sections
    # CrewAI returns task outputs keyed by agent type
    proofreading_output = None
    structure_output = None
    citations_output = None
    consistency_output = None
    plagiarism_output = None
    vision_output = None
    pdf_report_path = None

    if isinstance(result, dict):
        # Extract PDF report path
        pdf_report_path = result.get("pdf_report_path")
        
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
            pdf_report_path=pdf_report_path,
        ).dict()
    )


@router.get("/report/{file_id}")
async def get_report_pdf(file_id: str):
    """
    Download the PDF analysis report for a specific file.
    
    Args:
        file_id: The unique identifier of the analyzed file
    
    Returns:
        PDF file as a downloadable response
    """
    # Look for existing report in storage/reports directory
    reports_dir = "storage/reports"
    
    if not os.path.exists(reports_dir):
        raise HTTPException(status_code=404, detail="Reports directory not found")
    
    # Find report file matching the file_id
    matching_files = [
        f for f in os.listdir(reports_dir) 
        if f.startswith(f"analysis_report_{file_id}") and f.endswith(".pdf")
    ]
    
    if not matching_files:
        raise HTTPException(
            status_code=404, 
            detail=f"No PDF report found for file_id: {file_id}. Run analysis first."
        )
    
    # Get the most recent report (sorted by name which includes timestamp)
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
    This endpoint can be used if the PDF wasn't generated during analysis.
    
    Args:
        file_id: The unique identifier of the analyzed file
    
    Returns:
        Path to the generated PDF report
    """
    try:
        # First, run the analysis to get results
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
            # Try generating PDF manually
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
