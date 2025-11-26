"""
Test script for PDF parsing functionality.
Tests the parse_pdf_to_text_and_images function with sample PDFs.
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.pdf_parser import parse_pdf_to_text_and_images
from app.utils.logging import logger


def test_pdf_parser_with_sample():
    """Test PDF parser with a sample PDF if available."""
    
    # Check for sample PDFs in common locations
    sample_pdf_paths = [
        "/home/smayan/Desktop/Research-Paper-Analyst/backend/storage/uploads/",
        "/home/smayan/Desktop/Research-Paper-Analyst/downloads/",
        "/tmp/sample.pdf",
    ]
    
    pdf_file = None
    for path in sample_pdf_paths:
        if os.path.isdir(path):
            pdfs = list(Path(path).glob("*.pdf"))
            if pdfs:
                pdf_file = str(pdfs[0])
                break
    
    if not pdf_file:
        print("\n❌ No PDF files found in common locations.")
        print("   Please provide a PDF file first.")
        print("\n📝 To test with your own PDF:")
        print("   1. Place a PDF in: /home/smayan/Desktop/Research-Paper-Analyst/backend/storage/uploads/")
        print("   2. Run: python test_pdf_parser.py <path_to_pdf>")
        return False
    
    return test_pdf_file(pdf_file)


def test_pdf_file(pdf_path: str) -> bool:
    """
    Test parsing a specific PDF file.
    
    Args:
        pdf_path: Path to the PDF file to test
    
    Returns:
        bool: True if test passed, False otherwise
    """
    
    print(f"\n{'='*70}")
    print(f"Testing PDF Parser")
    print(f"{'='*70}\n")
    
    # Verify file exists
    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        return False
    
    print(f"📄 Testing file: {pdf_path}")
    print(f"📊 File size: {os.path.getsize(pdf_path) / 1024:.2f} KB\n")
    
    try:
        # Parse the PDF
        print("🔄 Parsing PDF...")
        result = parse_pdf_to_text_and_images(pdf_path)
        
        # Validate result
        if not isinstance(result, dict):
            print(f"❌ Result is not a dict: {type(result)}")
            return False
        
        if "text" not in result or "images" not in result:
            print(f"❌ Result missing required keys. Got: {result.keys()}")
            return False
        
        text = result["text"]
        images = result["images"]
        
        # Print results
        print(f"✅ Parse successful!\n")
        print(f"📋 Text Statistics:")
        print(f"   - Total characters: {len(text):,}")
        print(f"   - Total words: {len(text.split()):,}")
        print(f"   - Number of lines: {len(text.splitlines()):,}")
        print(f"   - Images found: {len(images)}")
        
        # Print first 500 characters
        print(f"\n📄 First 500 characters of extracted text:")
        print(f"   {'-'*60}")
        first_chunk = text[:500].replace('\n', '\n   ')
        print(f"   {first_chunk}")
        print(f"   {'-'*60}")
        
        # Print last 300 characters
        print(f"\n📄 Last 300 characters of extracted text:")
        print(f"   {'-'*60}")
        last_chunk = text[-300:].replace('\n', '\n   ')
        print(f"   {last_chunk}")
        print(f"   {'-'*60}\n")
        
        # Show sample of middle content
        if len(text) > 1000:
            mid_start = len(text) // 2
            mid_end = mid_start + 400
            print(f"📄 Sample from middle (chars {mid_start}-{mid_end}):")
            print(f"   {'-'*60}")
            mid_chunk = text[mid_start:mid_end].replace('\n', '\n   ')
            print(f"   {mid_chunk}")
            print(f"   {'-'*60}\n")
        
        print(f"{'='*70}")
        print(f"✅ All tests passed!")
        print(f"{'='*70}\n")
        
        return True
    
    except Exception as e:
        print(f"❌ Error parsing PDF: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_pdfs(directory: str) -> None:
    """
    Test parsing multiple PDF files in a directory.
    
    Args:
        directory: Path to directory containing PDFs
    """
    
    if not os.path.isdir(directory):
        print(f"❌ Directory not found: {directory}")
        return
    
    pdf_files = list(Path(directory).glob("*.pdf"))
    
    if not pdf_files:
        print(f"❌ No PDF files found in: {directory}")
        return
    
    print(f"\n{'='*70}")
    print(f"Testing {len(pdf_files)} PDF files in: {directory}")
    print(f"{'='*70}\n")
    
    passed = 0
    failed = 0
    
    for pdf_file in pdf_files:
        if test_pdf_file(str(pdf_file)):
            passed += 1
        else:
            failed += 1
        print()
    
    print(f"\n{'='*70}")
    print(f"Summary: {passed} passed, {failed} failed")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test PDF parser functionality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with first PDF found in uploads directory
  python test_pdf_parser.py
  
  # Test with specific PDF
  python test_pdf_parser.py /path/to/file.pdf
  
  # Test multiple PDFs in directory
  python test_pdf_parser.py /path/to/pdf/directory --batch
        """
    )
    
    parser.add_argument(
        "pdf_path",
        nargs="?",
        default=None,
        help="Path to PDF file or directory"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Test all PDFs in directory (requires --pdf_path to be a directory)"
    )
    
    args = parser.parse_args()
    
    if args.pdf_path is None:
        # Test with sample
        test_pdf_parser_with_sample()
    elif args.batch and os.path.isdir(args.pdf_path):
        # Test multiple PDFs
        test_multiple_pdfs(args.pdf_path)
    else:
        # Test single PDF
        test_pdf_file(args.pdf_path)
