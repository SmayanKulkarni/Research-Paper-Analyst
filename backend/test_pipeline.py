"""
Integration test for the complete PDF analysis pipeline.
Tests: Upload → Parse → Orchestration → Analysis
"""

import json
import os
from pathlib import Path
from typing import Optional
import sys

sys.path.insert(0, str(Path(__file__).parent))

from app.services.pdf_parser import parse_pdf_to_text_and_images
from app.crew.orchestrator import run_full_analysis
from app.utils.logging import logger


def find_sample_pdf() -> Optional[str]:
    """Find a sample PDF in common locations."""
    
    search_paths = [
        "/home/smayan/Desktop/Research-Paper-Analyst/backend/storage/uploads/",
        "/home/smayan/Desktop/Research-Paper-Analyst/downloads/",
        "./storage/uploads/",
    ]
    
    for path in search_paths:
        if os.path.isdir(path):
            pdfs = list(Path(path).glob("*.pdf"))
            if pdfs:
                return str(pdfs[0])
    
    return None


def test_full_pipeline(pdf_path: str) -> bool:
    """
    Test the complete analysis pipeline.
    
    Args:
        pdf_path: Path to PDF file
    
    Returns:
        bool: True if successful
    """
    
    print(f"\n{'='*70}")
    print(f"Full Pipeline Analysis Test")
    print(f"{'='*70}\n")
    
    # Step 1: Verify PDF exists
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return False
    
    print(f"📄 PDF: {pdf_path}")
    print(f"📊 Size: {os.path.getsize(pdf_path) / 1024:.2f} KB\n")
    
    try:
        # Step 2: Parse PDF
        print("📖 Step 1: Parsing PDF...")
        pdf_data = parse_pdf_to_text_and_images(pdf_path)
        text = pdf_data["text"]
        
        if not text or len(text.strip()) == 0:
            print("❌ No text extracted from PDF")
            return False
        
        print(f"✅ PDF parsed successfully")
        print(f"   - Characters extracted: {len(text):,}")
        print(f"   - Words: {len(text.split()):,}\n")
        
        # Step 3: Show sample
        print(f"📋 Sample text (first 300 chars):")
        print(f"   {'-'*60}")
        sample = text[:300].replace('\n', ' ')
        print(f"   {sample}...")
        print(f"   {'-'*60}\n")
        
        # Step 4: Run full analysis
        print("⚙️  Step 2: Running CrewAI analysis pipeline...")
        print(f"   This will run 6 agents (Citation, Structure, Consistency,")
        print(f"   Plagiarism, Proofreader, Vision) on the document.\n")
        
        analysis_result = run_full_analysis(
            text=text,
            images=pdf_data.get("images", [])
        )
        
        print(f"✅ Analysis completed\n")
        
        # Step 5: Display results
        print(f"{'='*70}")
        print(f"Analysis Results")
        print(f"{'='*70}\n")
        
        # Pretty print results
        result_json = json.dumps(analysis_result, indent=2)
        print(result_json)
        
        print(f"\n{'='*70}")
        print(f"✅ Full pipeline test passed!")
        print(f"{'='*70}\n")
        
        return True
    
    except Exception as e:
        print(f"❌ Error during pipeline test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_parsing_only(pdf_path: str) -> bool:
    """Test just the PDF parsing step (faster for debugging)."""
    
    print(f"\n{'='*70}")
    print(f"PDF Parsing Test Only")
    print(f"{'='*70}\n")
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return False
    
    try:
        print(f"📄 Parsing: {pdf_path}")
        result = parse_pdf_to_text_and_images(pdf_path)
        
        text = result["text"]
        images = result["images"]
        
        print(f"✅ Parse successful!")
        print(f"\n📊 Results:")
        print(f"   - Text length: {len(text):,} characters")
        print(f"   - Words: {len(text.split()):,}")
        print(f"   - Lines: {len(text.splitlines()):,}")
        print(f"   - Images: {len(images)}")
        
        # Show first 500 chars
        print(f"\n📝 First 500 characters:")
        print(f"   {'-'*60}")
        print(f"   {text[:500]}")
        print(f"   {'-'*60}\n")
        
        return True
    
    except Exception as e:
        print(f"❌ Parse failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test PDF analysis pipeline",
        epilog="""
Examples:
  # Test parsing only (fast)
  python test_pipeline.py --parse-only
  
  # Test full pipeline (slow - runs all 6 agents)
  python test_pipeline.py --full
  
  # Test with specific PDF
  python test_pipeline.py --full /path/to/paper.pdf
        """
    )
    
    parser.add_argument(
        "--parse-only",
        action="store_true",
        help="Test parsing only (faster)"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Test full pipeline with CrewAI analysis"
    )
    parser.add_argument(
        "pdf_path",
        nargs="?",
        help="Path to PDF file (optional - will search for sample)"
    )
    
    args = parser.parse_args()
    
    # Find PDF if not provided
    pdf_path = args.pdf_path
    if not pdf_path:
        pdf_path = find_sample_pdf()
        if not pdf_path:
            print("\n❌ No PDF file provided and none found in uploads directory")
            print("\n📝 Usage:")
            print("   python test_pipeline.py --parse-only /path/to/pdf.pdf")
            print("   python test_pipeline.py --full /path/to/pdf.pdf")
            sys.exit(1)
    
    # Run appropriate test
    if args.full:
        success = test_full_pipeline(pdf_path)
    else:
        success = test_parsing_only(pdf_path)
    
    sys.exit(0 if success else 1)
