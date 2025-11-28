#!/usr/bin/env python
"""
Batch Ingestion Script
----------------------
Scans a directory for PDF files and runs the Paper Discovery Service on them.
This populates your local knowledge base (Parquet + FAISS) with related papers
without running the expensive AI Agent analysis.

Usage: 
    python batch_ingest.py "C:\Path\To\Papers"
    or just run and paste path interactively.
"""

import sys
import os
import time
from pathlib import Path

# Add backend directory to Python path to allow imports from 'app'
sys.path.insert(0, str(Path(__file__).parent))

from app.services.paper_discovery import PaperDiscoveryService
from app.utils.logging import logger

def process_folder(folder_path: str):
    folder = Path(folder_path)
    
    if not folder.exists() or not folder.is_dir():
        print(f"❌ Error: Invalid directory: {folder_path}")
        return

    # Find all PDFs
    pdf_files = list(folder.glob("*.pdf"))
    
    if not pdf_files:
        print(f"ℹ️  No PDF files found in {folder_path}")
        return

    print(f"\nFound {len(pdf_files)} PDFs to process...")
    print("=" * 60)

    discovery_service = PaperDiscoveryService()
    
    success_count = 0
    skipped_count = 0
    total_new_papers = 0

    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_path.name}")
        
        try:
            # Run discovery (finds ArXiv ID -> downloads similar -> indexes to FAISS/Parquet)
            new_records = discovery_service.find_similar_papers(str(pdf_path))
            
            if new_records:
                count = len(new_records)
                print(f"   ✅ Success: Indexed {count} related papers.")
                total_new_papers += count
                success_count += 1
            else:
                print("   ⚠️  Skipped: No ID found or no new related papers.")
                skipped_count += 1
                
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            logger.error(f"Failed to process {pdf_path}: {e}")

    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print(f"Files Processed: {success_count}")
    print(f"Files Skipped:   {skipped_count}")
    print(f"Total New Papers Added to DB: {total_new_papers}")
    print("=" * 60)

def main():
    print("==================================================")
    print("   Research Paper Knowledge Base Builder")
    print("==================================================")
    
    # Get user input interactively if no args
    if len(sys.argv) > 1:
        input_path = " ".join(sys.argv[1:])
    else:
        input_path = input("\nPlease paste the folder path containing PDFs: ").strip()
    
    # Sanitize input
    path_str = input_path.strip('"').strip("'")
    path_obj = Path(path_str)

    if path_obj.is_file() and path_obj.suffix.lower() == ".pdf":
        # Handle single file case seamlessly
        print(f"\nDetected single file. Processing...")
        discovery_service = PaperDiscoveryService()
        discovery_service.find_similar_papers(str(path_obj))
        print("\nDone.")
    elif path_obj.is_dir():
        # Handle batch folder
        process_folder(str(path_obj))
    else:
        print("\n❌ Error: Path is not a valid folder or PDF file.")
        sys.exit(1)

if __name__ == "__main__":
    main()