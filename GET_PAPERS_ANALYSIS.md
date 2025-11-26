# get_papers.py Pipeline Analysis

## Overview
`get_papers.py` uses **embedding-based similarity search** to find related papers.

## Pipeline Steps

### 1. Load Embedding Model
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2")
```
- Uses pre-trained sentence embeddings
- Fast, deterministic, no LLM calls
- Creates dense vector representations of text

### 2. Get Target Paper
```python
paper_id = "2511.20636"
search = arxiv.Search(id_list=[paper_id])
paper = list(search.results())[0]
target_abstract = paper.summary
```
- Fetches a known paper from arXiv
- Extracts its abstract

### 3. Embed Target Paper
```python
target_emb = model.encode(target_abstract, convert_to_tensor=True)
```
- Converts abstract to 384-dimensional vector
- Captures semantic meaning

### 4. Search for Candidate Papers
```python
search_query = "cat:cs.CL"  # Computer Vision papers
results = arxiv.Search(query=search_query, max_results=200)
candidate_papers = [r for r in results.results() if r.entry_id != paper_id]
```
- Searches by category (cs.CL = Computer Science, Computation and Language)
- Gets up to 200 candidates
- Excludes the original paper

### 5. Embed Candidate Papers
```python
candidate_abstracts = [r.summary for r in candidate_papers]
candidate_embs = model.encode(candidate_abstracts, convert_to_tensor=True)
```
- Converts all candidate abstracts to vectors
- Batch processing is efficient

### 6. Compute Similarity
```python
from sentence_transformers import util
cos_scores = util.cos_sim(target_emb, candidate_embs)[0]
```
- Uses cosine similarity
- Fast vector operation
- Returns scores 0-1 (1 = identical, 0 = unrelated)

### 7. Get Top-K Similar Papers
```python
top_k = 10
top_results = cos_scores.topk(top_k)
```
- Selects top 10 most similar papers
- Returns similarity scores

### 8. Download PDFs
```python
for score, idx in zip(top_results.values, top_results.indices):
    p = candidate_papers[idx]
    p.download_pdf(dirpath=download_dir, filename=f"{p.get_short_id()}.pdf")
```
- Downloads PDF for each top paper
- Stores locally

## Key Advantages

| Aspect | Web Scraping | Embedding-Based Similarity |
|--------|--------------|---------------------------|
| **Speed** | Slow (HTTP requests) | Fast (batch vector ops) |
| **Reliability** | Fragile (site changes, rate limits) | Robust (arXiv API) |
| **Accuracy** | Variable (parsing errors) | Precise (semantic similarity) |
| **Cost** | Data usage, API limits | Zero (local embeddings) |
| **Reproducibility** | Non-deterministic | Deterministic |
| **Model** | Keyword/regex matching | Semantic understanding |

## Example Flow

```
Input: Paper about "Deep Learning for NLP"
  ↓
Extract abstract: "We propose a transformer-based model..."
  ↓
Embed abstract to 384-dim vector
  ↓
Search arXiv category cs.CL for 200 papers
  ↓
Embed all 200 candidates
  ↓
Compute cosine similarity scores
  ↓
Sort by similarity
  ↓
Top 10: Papers about transformers, NLP, deep learning
  ↓
Download PDFs
```

## Why This Works Better

1. **Semantic Understanding**: Embeddings capture meaning, not just keywords
2. **Fast**: No network requests (except arXiv metadata fetch)
3. **Scalable**: Can search thousands of papers locally
4. **No Parsing**: No HTML/PDF parsing fragility
5. **Deterministic**: Same input = same output every time
6. **No Rate Limits**: Only limited by arXiv API (very generous)

## Dependencies
- `arxiv` - arXiv API client (already used)
- `sentence-transformers` - Pre-trained embeddings (already in requirements)
- `torch` - Tensor operations (already in requirements)

## Current Project Usage

Where to apply this:
1. **Citation Paper Discovery** - Find similar papers to cited works
2. **Plagiarism Detection** - Find similar papers in Pinecone
3. **Related Work Section** - Suggest papers for comparison
4. **Research Exploration** - Suggest follow-up papers to read
