import requests
import os

API_BASE = "http://127.0.0.1:8000"

pdf_path = "/home/smayan/Documents/Question_answering_system_on_education_acts_using_NLP_techniques.pdf"

print(f"Opening: {pdf_path}")
with open(pdf_path, "rb") as f:
    files = {"file": ("paper.pdf", f, "application/pdf")}
    r = requests.post(f"{API_BASE}/api/uploads/", files=files)

print("Uploaded:", r.text)
data = r.json()
file_id = data["file_id"]
print("File ID:", file_id)

print("\n--- ANALYSIS RESPONSE ---\n")
resp = requests.post(f"{API_BASE}/api/analyze/", params={"file_id": file_id})
print(resp.text)
