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

try:
    from app.services.pdf_parser_layout import parse_pdf_to_markdown
except ImportError:
    print("⚠️ Warning: 'pdf_parser_layout' not found. Ensure backend/app/services/pdf_parser_layout.py exists.")
    sys.exit(1)

from app.crew.orchestrator import run_full_analysis
from app.services.paper_discovery import PaperDiscoveryService
from app.utils.logging import logger

def print_report(analysis_result: dict):
    print("\n" + "="*80)
    print("FINAL RESEARCH PAPER ANALYSIS REPORT".center(80))
    print("="*80 + "\n")

    # Updated sections to match consolidated agents (no plagiarism)
    sections = [
        ("language_quality", "📝 LANGUAGE QUALITY (Grammar, Clarity, Consistency)"),
        ("structure", "🏗️  STRUCTURE & ORGANIZATION"),
        ("citations", "📖 CITATION ANALYSIS"),
        ("math_review", "🔢 MATHEMATICAL CONTENT REVIEW"),
        ("vision", "👁️  VISUAL ANALYSIS"),
    ]

    for key, title in sections:
        content = analysis_result.get(key)
        
        if not content:
            continue

        print(f"{title}")
        print("-" * 80)
        
        # If content is already a dict (from Pydantic), dump it nicely
        if isinstance(content, (dict, list)):
            print(json.dumps(content, indent=2))
        else:
            # Fallback for raw text strings
            cleaned_content = str(content).strip().strip('"').strip("'")
            cleaned_content = cleaned_content.replace("\\n", "\n")
            print(cleaned_content)
            
        print("\n" + "."*80 + "\n")

def main():
    print("==================================================")
    print("   Research Paper Analyst - Local Execution Mode")
    print("==================================================")
    
    if len(sys.argv) > 1:
        pdf_path_input = " ".join(sys.argv[1:])
    else:
        pdf_path_input = input("\nPlease paste the full path to the PDF file: ").strip()
    
    pdf_path = pdf_path_input.strip('"').strip("'")
    
    if not pdf_path or not Path(pdf_path).exists():
        print(f"\n❌ Error: File not found at:\n{pdf_path}")
        sys.exit(1)
    
    print(f"\n--- STEP 1: Paper Discovery & Knowledge Base Update ---")
    try:
        discovery_service = PaperDiscoveryService()
        found_papers = discovery_service.find_similar_papers(pdf_path)
        if found_papers:
            print(f"✅ Found and saved {len(found_papers)} related papers.")
        else:
            print("ℹ️  No related papers found or ID extraction failed.")
    except Exception as e:
        print(f"❌ Discovery step failed: {e}")

    print(f"\n--- STEP 2: Parsing PDF Content (Layout-Aware) ---")
    result = parse_pdf_to_markdown(pdf_path)
    
    if not result["text"]:
        print("❌ Error: Could not extract text from the PDF.")
        sys.exit(1)

    print(f"\n--- STEP 3: Running CrewAI Agents ---")
    # Pass pdf_path for image extraction within orchestrator
    analysis = run_full_analysis(
        text=result["text"],
        pdf_path=pdf_path,  # Enable image extraction for vision analysis
        enable_vision=True,
        enable_citation=True,
    )
    
    print_report(analysis)

if __name__ == "__main__":
    main()