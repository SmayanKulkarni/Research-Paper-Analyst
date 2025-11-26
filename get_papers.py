import arxiv
from sentence_transformers import SentenceTransformer, util
import os

# ----------------------------------------------------
# 0. Create download directory
# ----------------------------------------------------

import re
import PyPDF2

def find_arxiv_id_in_pdf(pdf_path):
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""

    pattern = r'(?:arXiv:)?(\d{4}\.\d{4,5})(?:v\d+)?'
    match = re.search(pattern, text)
    return match.group(1) if match else None

id = find_arxiv_id_in_pdf("/home/smayan/Desktop/Research-Paper-Analyst/downloads/1906.00579v3.pdf")

download_dir = "downloads"
os.makedirs(download_dir, exist_ok=True)

# ----------------------------------------------------
# 1. Load an embedding model
# ----------------------------------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")

# ----------------------------------------------------
# 2. Get abstract of a given paper
# ----------------------------------------------------
paper_id = id  # example
search = arxiv.Search(id_list=[paper_id])
paper = list(search.results())[0]
target_abstract = paper.summary

# ----------------------------------------------------
# 3. Encode the target paper
# ----------------------------------------------------
target_emb = model.encode(target_abstract, convert_to_tensor=True)

# ----------------------------------------------------
# 4. Search for candidate papers in the same category
# ----------------------------------------------------
search_query = "cat:cs.CL"  # choose your category
results = arxiv.Search(query=search_query, max_results=200)

candidate_papers = []
candidate_abstracts = []

for r in results.results():
    if r.entry_id.endswith(paper_id):
        continue
    candidate_papers.append(r)
    candidate_abstracts.append(r.summary)

# ----------------------------------------------------
# 5. Encode candidate abstracts
# ----------------------------------------------------
candidate_embs = model.encode(candidate_abstracts, convert_to_tensor=True)

# ----------------------------------------------------
# 6. Compute similarities
# ----------------------------------------------------
cos_scores = util.cos_sim(target_emb, candidate_embs)[0]

# ----------------------------------------------------
# 7. Get top-k similar papers
# ----------------------------------------------------
top_k = 10
top_results = cos_scores.topk(top_k)

print("Top similar papers:\n")

for score, idx in zip(top_results.values, top_results.indices):
    p = candidate_papers[idx]
    print(f"{score:.4f} - {p.title} ({p.entry_id})")

    # ----------------------------------------------------
    # 8. Download the PDF
    # ----------------------------------------------------
    pdf_path = os.path.join(download_dir, f"{p.get_short_id()}.pdf")
    print(f"  Downloading to: {pdf_path}")

    p.download_pdf(dirpath=download_dir, filename=f"{p.get_short_id()}.pdf")
