#!/usr/bin/env python
"""
Run CrewAI analysis on a PDF file locally.
Usage: Run the script, then paste the file path when prompted.
"""

import sys
import json
import os
from pathlib import Path

# Add backend directory to Python path to allow imports from 'app'
sys.path.insert(0, str(Path(__file__).parent))

# Try importing the layout-aware parser, fall back to simple text parser if missing
try:
    from app.services.pdf_parser_layout import parse_pdf_to_markdown
except ImportError:
    print("⚠️ Warning: 'pdf_parser_layout' not found. Ensure backend/app/services/pdf_parser_layout.py exists.")
    sys.exit(1)

from app.crew.orchestrator import run_full_analysis
from app.services.paper_discovery import PaperDiscoveryService
from app.utils.logging import logger

def print_report(analysis_result: dict):
    """
    Formats and prints the analysis result as a structured text report.
    """
    print("\n" + "="*80)
    print("FINAL RESEARCH PAPER ANALYSIS REPORT".center(80))
    print("="*80 + "\n")

    # Define sections mapping (Key -> Display Title)
    sections = [
        ("proofreading", "📝 PROOFREADING & EDITING"),
        ("structure", "🏗️  STRUCTURE & FLOW"),
        ("consistency", "🔄 INTERNAL CONSISTENCY"),
        ("citations", "📖 CITATION VERIFICATION"),
        ("plagiarism", "🕵️  PLAGIARISM CHECK"),
        ("vision", "👁️  VISUAL ANALYSIS"),
    ]

    for key, title in sections:
        content = analysis_result.get(key)
        
        # Skip empty sections
        if not content or str(content).strip().lower() in ["null", "none", ""]:
            continue

        print(f"{title}")
        print("-" * 80)
        
        # If content is a structured object (list/dict), pretty print it
        if isinstance(content, (dict, list)):
            print(json.dumps(content, indent=2))
        else:
            # Otherwise treat as text (Markdown strings from LLM)
            print(str(content).strip())
            
        print("\n" + "."*80 + "\n")

def main():
    print("==================================================")
    print("   Research Paper Analyst - Local Execution Mode")
    print("==================================================")
    
    # Get user input interactively
    # Check if arguments were passed, otherwise ask for input
    if len(sys.argv) > 1:
        # Join arguments to handle unquoted paths with spaces
        pdf_path_input = " ".join(sys.argv[1:])
    else:
        pdf_path_input = input("\nPlease paste the full path to the PDF file: ").strip()
    
    # Sanitize the input: remove surrounding quotes that terminals/OS might add
    pdf_path = pdf_path_input.strip('"').strip("'")
    
    if not pdf_path:
        print("Error: No path provided.")
        sys.exit(1)

    if not Path(pdf_path).exists():
        print(f"\n❌ Error: File not found at:\n{pdf_path}")
        print("Please check the path and try again.")
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
            print(f"✅ Found and saved {len(found_papers)} related papers to Parquet/Pinecone.")
            for p in found_papers:
                print(f"   - {p['title']} (Similarity: {p.get('similarity', 0):.2f})")
        else:
            print("ℹ️  No related papers found or ID extraction failed (check logs).")
            
    except Exception as e:
        print(f"❌ Discovery step failed: {e}")

    # ---------------------------------------------------------
    # STEP 2: PDF Parsing
    # ---------------------------------------------------------
    print(f"\n--- STEP 2: Parsing PDF Content (Layout-Aware) ---")
    
    result = parse_pdf_to_markdown(pdf_path)
    
    if not result["text"]:
        print("❌ Error: Could not extract text from the PDF.")
        sys.exit(1)

    # ---------------------------------------------------------
    # STEP 3: CrewAI Analysis
    # ---------------------------------------------------------
    print(f"\n--- STEP 3: Running CrewAI Agents ---")
    
    analysis = run_full_analysis(
        text=result["text"],
        images=result.get("images", [])
    )
    
    # ---------------------------------------------------------
    # STEP 4: Final Output
    # ---------------------------------------------------------
    print_report(analysis)


if __name__ == "__main__":
    main()