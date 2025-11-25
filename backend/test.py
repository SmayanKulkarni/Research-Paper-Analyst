import requests
import json
import time
import os
import sys

API_BASE = "http://127.0.0.1:8000"

PDF_PATH = "/home/smayan/Documents/Question_answering_system_on_education_acts_using_NLP_techniques.pdf"


def print_header(text):
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80 + "\n")


def safe_print_json(label, raw):
    print_header(label)
    try:
        parsed = json.loads(raw)
        print(json.dumps(parsed, indent=4))
    except:
        print(raw)


def upload_file(pdf_path):
    print_header(f"Uploading PDF: {pdf_path}")

    if not os.path.exists(pdf_path):
        print(f"❌ FILE NOT FOUND: {pdf_path}")
        sys.exit(1)

    with open(pdf_path, "rb") as f:
        files = {"file": ("paper.pdf", f, "application/pdf")}
        try:
            r = requests.post(f"{API_BASE}/api/uploads/", files=files, timeout=60)
            r.raise_for_status()
        except Exception as e:
            print("❌ Upload Failed:", e)
            print("Raw Response:", getattr(r, "text", None))
            sys.exit(1)

    try:
        data = r.json()
    except:
        print("❌ Upload did not return JSON:", r.text)
        sys.exit(1)

    if "file_id" not in data:
        print("❌ Upload returned invalid response:", data)
        sys.exit(1)

    print("✅ Upload Successful!")
    print("File ID:", data["file_id"])
    return data["file_id"]


def analyze_file(file_id):
    print_header(f"Running Analysis on File ID: {file_id}")

    try:
        r = requests.post(
            f"{API_BASE}/api/analyze/",
            params={"file_id": file_id},
            timeout=300,  # allow long-running jobs
        )
    except requests.exceptions.ReadTimeout:
        print("⚠️ Server took too long. Retrying once...")
        r = requests.post(
            f"{API_BASE}/api/analyze/",
            params={"file_id": file_id},
            timeout=300,
        )
    except Exception as e:
        print("❌ Analysis Request Failed:", e)
        return None

    if r.status_code >= 500:
        print("\n❌ SERVER ERROR (500):")
        print(r.text)
        return None

    return r.text


def main():
    file_id = upload_file(PDF_PATH)
    result = analyze_file(file_id)

    if result:
        safe_print_json("ANALYSIS RESPONSE", result)
    else:
        print("❌ No result returned from analysis.")


if __name__ == "__main__":
    main()
