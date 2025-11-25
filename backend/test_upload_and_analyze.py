"""Simple test script for Research-Paper-Analyst backend.

Usage:
    python3 test_upload_and_analyze.py --pdf samples/example.pdf --server http://localhost:8000 --wait 12

What it does:
- Uploads the provided PDF to POST /api/uploads/
- Waits `--wait` seconds to allow background crawling to run (default 10)
- Calls POST /api/analyze/?file_id=<returned_id> and prints the JSON result

Requires: httpx (already in requirements.txt)
"""

import argparse
import time
import httpx
import sys
import json
from pathlib import Path


def upload_pdf(server: str, pdf_path: Path) -> dict:
    url = f"{server.rstrip('/')}/api/uploads/"
    with httpx.Client(timeout=60) as client:
        with pdf_path.open("rb") as fh:
            files = {"file": (pdf_path.name, fh, "application/pdf")}
            print(f"Uploading {pdf_path} to {url} ...")
            r = client.post(url, files=files)
    r.raise_for_status()
    return r.json()


def analyze_file(server: str, file_id: str) -> dict:
    url = f"{server.rstrip('/')}/api/analyze/"
    params = {"file_id": file_id}
    with httpx.Client(timeout=120) as client:
        print(f"Requesting analysis for file_id={file_id} ...")
        r = client.post(url, params=params)
    r.raise_for_status()
    return r.json()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pdf", required=True, help="Path to PDF file to upload")
    p.add_argument("--server", default="http://localhost:8000", help="Base URL of the API server")
    p.add_argument("--wait", type=int, default=10, help="Seconds to wait after upload before calling analyze")
    args = p.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        sys.exit(2)

    try:
        up = upload_pdf(args.server, pdf_path)
    except Exception as e:
        print(f"Upload failed: {e}")
        sys.exit(1)

    print("Upload response:")
    print(json.dumps(up, indent=2))

    file_id = up.get("file_id") or up.get("fileId")
    if not file_id:
        print("No file_id returned by upload endpoint. Aborting.")
        sys.exit(1)

    print(f"Waiting {args.wait}s for background crawl to run (if enabled)...")
    time.sleep(args.wait)

    try:
        analysis = analyze_file(args.server, file_id)
    except Exception as e:
        print(f"Analyze failed: {e}")
        sys.exit(1)

    print("Analysis result:")
    print(json.dumps(analysis, indent=2))


if __name__ == "__main__":
    main()
