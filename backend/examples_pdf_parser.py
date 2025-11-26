"""
Simple examples showing how to use the PDF parser in your code.
"""

from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.pdf_parser import parse_pdf_to_text_and_images


# Example 1: Basic usage
def example_1_basic_parsing():
    """Simplest way to parse a PDF."""
    
    pdf_path = "/home/smayan/Desktop/Research-Paper-Analyst/downloads/2007.07825v1.pdf"
    
    result = parse_pdf_to_text_and_images(pdf_path)
    
    text = result["text"]
    images = result["images"]
    
    print(f"Extracted {len(text)} characters of text")
    print(f"Found {len(images)} images")
    print(f"\nFirst 200 chars: {text[:200]}\n")


# Example 2: Get detailed statistics
def example_2_text_statistics():
    """Get detailed information about extracted text."""
    
    pdf_path = "/home/smayan/Desktop/Research-Paper-Analyst/downloads/2007.07825v1.pdf"
    
    result = parse_pdf_to_text_and_images(pdf_path)
    text = result["text"]
    
    # Statistics
    num_chars = len(text)
    num_words = len(text.split())
    num_lines = len(text.splitlines())
    num_paragraphs = len(text.split("\n\n"))
    
    print(f"Text Statistics:")
    print(f"  Characters: {num_chars:,}")
    print(f"  Words: {num_words:,}")
    print(f"  Lines: {num_lines:,}")
    print(f"  Paragraphs: {num_paragraphs:,}")
    print(f"  Avg words per line: {num_words / max(1, num_lines):.1f}\n")


# Example 3: Split text into chunks
def example_3_chunk_text():
    """Split extracted text into chunks for processing."""
    
    pdf_path = "/home/smayan/Desktop/Research-Paper-Analyst/downloads/2007.07825v1.pdf"
    
    result = parse_pdf_to_text_and_images(pdf_path)
    text = result["text"]
    
    # Split by paragraphs
    paragraphs = text.split("\n\n")
    
    print(f"Document has {len(paragraphs)} paragraphs\n")
    
    # Show first 3 paragraphs
    for i, para in enumerate(paragraphs[:3], 1):
        if para.strip():
            words = len(para.split())
            print(f"Paragraph {i} ({words} words):")
            print(f"  {para[:100].strip()}...\n")


# Example 4: Extract sentences
def example_4_extract_sentences():
    """Extract individual sentences from the text."""
    
    pdf_path = "/home/smayan/Desktop/Research-Paper-Analyst/downloads/2007.07825v1.pdf"
    
    result = parse_pdf_to_text_and_images(pdf_path)
    text = result["text"]
    
    # Simple sentence splitting (replace newlines with spaces first)
    text_cleaned = text.replace("\n", " ")
    
    # Split by periods, question marks, exclamation marks
    import re
    sentences = re.split(r'[.!?]+', text_cleaned)
    
    # Clean up
    sentences = [s.strip() for s in sentences if s.strip()]
    
    print(f"Found {len(sentences)} sentences\n")
    
    # Show first 5 sentences
    for i, sent in enumerate(sentences[:5], 1):
        print(f"{i}. {sent[:100]}...")
        print()


# Example 5: Find specific content
def example_5_search_content():
    """Search for specific keywords in the text."""
    
    pdf_path = "/home/smayan/Desktop/Research-Paper-Analyst/downloads/2007.07825v1.pdf"
    
    result = parse_pdf_to_text_and_images(pdf_path)
    text = result["text"].lower()
    
    # Search for keywords
    keywords = ["abstract", "introduction", "conclusion", "algorithm", "design"]
    
    print("Keyword search results:\n")
    for keyword in keywords:
        count = text.count(keyword)
        if count > 0:
            print(f"  ✅ '{keyword}': found {count} times")
        else:
            print(f"  ❌ '{keyword}': not found")
    print()


# Example 6: Process for analysis
def example_6_prepare_for_analysis():
    """Prepare text for analysis pipeline."""
    
    pdf_path = "/home/smayan/Desktop/Research-Paper-Analyst/downloads/2007.07825v1.pdf"
    
    result = parse_pdf_to_text_and_images(pdf_path)
    text = result["text"]
    images = result["images"]
    
    # Clean up text
    text_clean = text.strip()
    
    # Check if content is valid
    if len(text_clean) < 100:
        print("❌ Text too short for analysis")
        return
    
    print(f"✅ Text is ready for analysis")
    print(f"   - Length: {len(text_clean):,} characters")
    print(f"   - Estimated reading time: {len(text_clean.split()) / 200:.0f} minutes")
    print(f"   - Images to analyze: {len(images)}")
    print(f"\nSample for submission to analysis pipeline:")
    print(f"   {text_clean[:300]}...")
    print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run PDF parser examples"
    )
    parser.add_argument(
        "example",
        nargs="?",
        type=int,
        default=0,
        help="Example number to run (1-6), or 0 for all"
    )
    
    args = parser.parse_args()
    
    examples = {
        1: ("Basic Parsing", example_1_basic_parsing),
        2: ("Text Statistics", example_2_text_statistics),
        3: ("Chunk Text", example_3_chunk_text),
        4: ("Extract Sentences", example_4_extract_sentences),
        5: ("Search Keywords", example_5_search_content),
        6: ("Prepare for Analysis", example_6_prepare_for_analysis),
    }
    
    if args.example == 0:
        # Run all
        for num, (name, func) in sorted(examples.items()):
            print(f"\n{'='*60}")
            print(f"Example {num}: {name}")
            print(f"{'='*60}\n")
            func()
    elif args.example in examples:
        name, func = examples[args.example]
        print(f"\n{'='*60}")
        print(f"Example {args.example}: {name}")
        print(f"{'='*60}\n")
        func()
    else:
        print(f"❌ Invalid example number. Choose 1-6 or 0 for all")
