#!/usr/bin/env python
"""
Run CrewAI analysis on a PDF file locally.
Usage: python run_analysis.py /path/to/file.pdf
"""

import sys
import json
import os
from pathlib import Path

# Add backend directory to Python path to allow imports from 'app'
sys.path.insert(0, str(Path(__file__).parent))

from app.services.pdf_parser import parse_pdf_to_text_and_images
from app.crew.orchestrator import run_full_analysis
from app.services.paper_discovery import PaperDiscoveryService
from app.utils.logging import logger

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_analysis.py /path/to/file.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    # ---------------------------------------------------------
    # STEP 1: Paper Discovery (ArXiv & Parquet)
    # ---------------------------------------------------------
    print(f"\n--- STEP 1: Paper Discovery & Knowledge Base Update ---")
    print(f"Processing: {pdf_path}")
    
    try:
        discovery_service = PaperDiscoveryService()
        found_papers = discovery_service.find_similar_papers(pdf_path)
        
        if found_papers:
            print(f"✅ Found and saved {len(found_papers)} related papers to Parquet.")
            for p in found_papers:
                print(f"   - {p['title']} (Similarity: {p.get('similarity', 0):.2f})")
        else:
            print("ℹ️  No related papers found or ID extraction failed (check logs).")
            
    except Exception as e:
        print(f"❌ Discovery step failed: {e}")
        # We continue to analysis even if discovery fails

    # ---------------------------------------------------------
    # STEP 2: PDF Parsing
    # ---------------------------------------------------------
    print(f"\n--- STEP 2: Parsing PDF Content ---")
    result = parse_pdf_to_text_and_images(pdf_path)
    
    # ---------------------------------------------------------
    # STEP 3: CrewAI Analysis
    # ---------------------------------------------------------
    print(f"\n--- STEP 3: Running CrewAI Agents ---")
    # We pass the extracted text directly. 
    # file_id is None because this is a local run, preventing Orchestrator 
    # from trying to re-run discovery using web paths.
    analysis = run_full_analysis(
        text=result["text"],
        images=result.get("images", [])
    )
    
    print("\n--- Final Analysis Results ---")
    print(json.dumps(analysis, indent=2))


if __name__ == "__main__":
    main()