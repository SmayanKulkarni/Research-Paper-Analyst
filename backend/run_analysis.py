#!/usr/bin/env python
"""
Run CrewAI analysis on a PDF file.
Usage: python run_analysis.py /path/to/file.pdf
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.pdf_parser import parse_pdf_to_text_and_images
from app.crew.orchestrator import run_full_analysis


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_analysis.py /path/to/file.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    print(f"Parsing: {pdf_path}")
    result = parse_pdf_to_text_and_images(pdf_path)
    
    print(f"Running CrewAI analysis...")
    analysis = run_full_analysis(
        text=result["text"],
        images=result.get("images", [])
    )
    
    import json
    print(json.dumps(analysis, indent=2))


if __name__ == "__main__":
    main()
