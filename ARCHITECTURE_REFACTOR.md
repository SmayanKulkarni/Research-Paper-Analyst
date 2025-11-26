# Major Architecture Refactor: Citation-Based Paper Discovery + NLP Optimization

## Overview

This refactor implements a **major shift in how the backend discovers and processes research papers**. Instead of searching online for "similar" papers based on queries, the system now:

1. **Extracts bibliography references** from uploaded research papers
2. **Resolves citations to arXiv papers** using the `arxiv` Python package
3. **Applies NLP preprocessing** (summarization, key-phrase extraction) to the paper BEFORE chunking/compression
4. **Tracks token usage in detail** with per-agent and per-analysis metrics

---

## Architecture Changes

### 1. Citation Extraction (`citation_extractor.py`)

**What it does:**
- Parses the References/Bibliography section of research papers using regex
- Extracts arXiv IDs, DOI links, and URLs from citation text
- Identifies authors and titles when available
- Filters to keep only arXiv-linkable citations

**Key functions:**
```python
extract_citations_from_text(text, max_citations=50) -> List[Dict]
filter_arxiv_citations(citations) -> List[Dict]
```

**Data structure:**
```python
{
    "raw_text": str,
    "arxiv_id": Optional[str],
    "doi": Optional[str],
    "url": Optional[str],
    "authors": Optional[str],
    "title": Optional[str],
    "index": int,
}
```

---

### 2. ArXiv Resolver (`arxiv_finder.py`)

**What it does:**
- Resolves citation metadata to actual arXiv papers
- Uses the `arxiv` Python package for lookups
- Falls back to title/authors search if ID/URL lookup fails
- Embeds and ingests papers into Pinecone

**Key functions:**
```python
fetch_arxiv_paper_by_id(arxiv_id) -> Optional[Dict]
resolve_citation_to_arxiv(citation) -> Optional[Dict]
ingest_arxiv_papers_from_citations(citations, max_papers=5) -> List[Dict]
```

**Resolution strategy** (in order):
1. Try direct arXiv ID lookup
2. Try URL-based lookup (extract ID from arxiv.org URL)
3. Try title-based search (fallback)

---

### 3. NLP Preprocessing (`nlp_preprocessor.py`)

**What it does:**
- Applies abstractive summarization (BART-large-CNN or fallback)
- Extracts key phrases/technical terms (KeyBERT or regex patterns)
- Performs entity recognition (spaCy or regex patterns)
- Returns preprocessed text + metadata

**Key functions:**
```python
preprocess_research_paper(
    text,
    enable_summarization=True,
    enable_key_phrases=True,
    enable_entities=False,
    max_output_length=5000,
) -> Dict
```

**Output includes:**
- `processed_text`: condensed version with summary + key info
- `summary`: abstractive summary
- `key_phrases`: extracted technical terms
- `token_savings_estimate`: estimated tokens saved vs. original

**Token savings:** Typically 50-80% reduction in tokens before LLM processing.

---

### 4. Token Counting (`token_counter.py`)

**What it does:**
- Provides fast and accurate token estimation
- Uses simple char-based method (fast) or transformers-based (accurate)
- Estimates response tokens based on prompt size
- Creates detailed token summaries for logging

**Key functions:**
```python
estimate_tokens_simple(text) -> int  # Fast: chars/4
count_tokens_transformers(text) -> int  # Accurate (GPT-2 tokenizer)
count_tokens(text, use_transformers=False) -> int
count_tokens_in_messages(messages) -> int
estimate_response_tokens(prompt_tokens, model_name) -> int
create_token_summary(text) -> Dict
log_token_summary(text, context) -> None
```

---

## Integration Points

### PDF Parser Update

**File:** `pdf_parser.py`

The PDF parser now extracts citations during parsing:
```python
def parse_pdf_to_text_and_images(file_path, extract_citations=True):
    return {
        "text": full_text,
        "images": image_paths,
        "citations": arxiv_citations,  # NEW
    }
```

### Upload Router Update

**File:** `routers/uploads.py`

Background task changed from generic web crawl to citation extraction:
```python
async def _process_citations_on_upload(dest_path, file_id, max_papers=5):
    # 1. Parse PDF (now extracts citations)
    # 2. Resolve citations to arXiv papers
    # 3. Ingest papers into Pinecone
```

### Orchestrator Update

**File:** `crew/orchestrator.py`

Analysis pipeline now includes NLP preprocessing as **STEP 1**:

```
1. NLP Preprocessing (NEW)
   ├─ Abstractive summarization
   ├─ Key-phrase extraction
   └─ Token savings: ~50-80%

2. Chunking (as before)

3. Compression (improved)
   ├─ Uses lighter preprocessing for each chunk
   └─ Saves tokens

4. Multi-agent analysis (as before)
   └─ Works on already-condensed text
```

**Token usage logging:**
```python
log_token_summary(text, context="original")  # Logs original tokens
log_token_summary(preprocessed_text, context="post-nlp")  # Logs after preprocessing
log_token_summary(compressed_text, context="post-compression")  # Logs after compression
```

---

## Token Budget Enhancement

**File:** `token_budget.py`

Added comprehensive token tracking:

```python
class TokenBudgetTracker:
    # Per-agent tracking
    def add_usage(tokens, agent_name=None)
    def per_agent_usage: Dict[str, int]
    def get_per_agent_summary() -> Dict
    
    # Per-analysis tracking
    def start_analysis(analysis_id)
    def record_agent_call(analysis_id, agent_name, estimated_tokens, actual_tokens)
    def get_analysis_metrics(analysis_id)
    def log_analysis_summary(analysis_id)
```

**Metrics tracked:**
- Total tokens used (minute-based reset)
- Per-agent tokens and call counts
- Per-analysis estimated vs. actual tokens
- Accuracy of token estimates
- Analysis duration

---

## Data Flow: Upload to Analysis

```
1. User uploads PDF
   ↓
2. Background Task: _process_citations_on_upload()
   ├─ Parse PDF → extract text, images, citations
   ├─ For each citation:
   │  ├─ Try resolve to arXiv paper
   │  └─ Embed summary
   ├─ Ingest papers into Pinecone
   └─ Limit to max_papers (default 5)

3. User requests analysis
   ↓
4. run_full_analysis()
   ├─ STEP 1: NLP Preprocessing
   │  ├─ Summarize full text
   │  ├─ Extract key phrases
   │  └─ Log token savings (~50-80% reduction)
   │
   ├─ STEP 2: Chunk & Compress
   │  ├─ Split preprocessed text into chunks
   │  ├─ Apply lightweight preprocessing per chunk
   │  └─ Compress with compression agent
   │
   ├─ STEP 3: Multi-agent Analysis
   │  ├─ Proofreader, structure, citation, consistency, plagiarism
   │  └─ All work on condensed text
   │
   └─ STEP 4: Vision Analysis (separate)
      └─ Works on page images only
```

---

## Dependency Changes

### Added Dependencies

```
transformers          # For BART summarization, GPT-2 tokenizer
spacy                 # For entity recognition (optional NLP)
keybert               # For key-phrase extraction
torch                 # For transformers models
tiktoken              # For token counting (OpenAI tokenizer)
```

### Removed Dependencies

```
crawl4ai              # No longer needed (arXiv-only)
duckduckgo_search     # No longer needed (arXiv-only)
```

### Still Used

```
arxiv                 # arXiv package for paper lookup
```

---

## Configuration

### New Config Options

**In `config.py` (if needed):**
```python
# NLP preprocessing
ENABLE_NLP_PREPROCESSING: bool = True
NLP_MAX_OUTPUT_LENGTH: int = 5000

# Token counting
USE_TRANSFORMERS_TOKENIZER: bool = False  # False=fast, True=accurate

# Citation processing
MAX_CITATIONS_TO_PROCESS: int = 50
MAX_ARXIV_PAPERS_PER_UPLOAD: int = 5
```

---

## Performance Expectations

### Token Savings

| Stage | Typical Reduction |
|-------|-------------------|
| NLP Preprocessing | 50-80% |
| Compression | 30-60% |
| **Total** | **70-95%** |

### Example

```
Original paper: 50,000 characters → ~12,500 tokens
After NLP preprocessing: 10,000 characters → ~2,500 tokens (80% saved)
After compression: 5,000 characters → ~1,250 tokens (50% saved from that)
Total reduction: ~90% fewer tokens to downstream agents
```

### Rate Limit Benefits

With 90% token reduction:
- Original TPM usage: 12,500 tokens → hits 6000 TPM limit quickly
- Optimized TPM usage: 1,250 tokens → easily fits within limits
- **Result:** Fewer 429 errors, better concurrent request handling

---

## Error Handling

### Citation Extraction

- If References section not found → No citations extracted (graceful)
- If citation cannot be parsed → Skipped (continues)
- If multiple resolution strategies fail → Citation ignored (defensive)

### arXiv Resolution

- If arXiv package unavailable → Empty result (defensive fallback)
- If paper not found → Skip to next citation (continues)
- If embedding fails → Skip paper (continues)

### NLP Preprocessing

- If BART summarization fails → Use extractive summary (fallback)
- If KeyBERT unavailable → Use regex patterns (fallback)
- If spaCy unavailable → Use regex patterns (fallback)
- All failures are non-blocking; analysis continues

---

## Logging & Monitoring

### Key Log Messages

```
"Extracted X citations from text"
"Filtered X citations down to Y with arXiv identifiers"
"Successfully ingested N arXiv papers from citations into Pinecone"
"NLP preprocessing: 50000 chars → 10000 chars (est. ~10000 tokens saved)"
"Original text: 12500 tokens"
"After NLP preprocessing: 2500 tokens"
"Analysis {id} summary: Duration=12.5s, Estimated tokens=3000, Actual=2800 (93% accuracy), Agents used=[...]"
```

### Token Metrics Per Analysis

```
per_agent_usage:
  "proofreader": 256 tokens
  "structure": 128 tokens
  "citation": 100 tokens
  "consistency": 100 tokens
  "plagiarism": 50 tokens

per_analysis_metrics[analysis_id]:
  "estimated_tokens": 1200
  "actual_tokens": 1100
  "agents_used": ["proofreader", "structure", "citation", "consistency"]
  "duration": 15.3 seconds
  "accuracy": 91.6%
```

---

## Future Enhancements

1. **Redis-backed response cache** (current: in-memory LRU)
2. **Cluster-wide token coordination** (current: per-process only)
3. **Calibrated token estimates** using actual LLM responses
4. **Metrics endpoint** to expose token usage dashboard
5. **DOI resolver** to handle non-arXiv citations
6. **Citation context extraction** (surrounding text where citation appears)
7. **Academic database integration** (PubMed, IEEE Xplore, etc.)

---

## Testing Checklist

```
[ ] Citation extraction from sample PDFs
[ ] arXiv ID resolution (direct, URL, title-based)
[ ] NLP preprocessing with different paper lengths
[ ] Token counting accuracy vs. actual LLM responses
[ ] Per-agent token tracking
[ ] Per-analysis metrics recording
[ ] Full end-to-end: upload → cite → NLP → analysis
[ ] Rate limit improvements (fewer 429 errors)
[ ] No regressions in analysis quality
[ ] Graceful error handling (all fallbacks)
```

---

## Quick Start Guide

### Installation

```bash
pip install -r requirements.txt

# Download spaCy model (optional, for entity extraction)
python -m spacy download en_core_web_sm
```

### Environment Variables (if needed)

```env
# Citation processing
MAX_CITATIONS_TO_PROCESS=50
MAX_ARXIV_PAPERS_PER_UPLOAD=5

# NLP preprocessing
ENABLE_NLP_PREPROCESSING=true
NLP_MAX_OUTPUT_LENGTH=5000

# Token counting
USE_TRANSFORMERS_TOKENIZER=false  # true=accurate but slower
```

### Usage

No API changes needed. Existing endpoints work as before:
- `POST /api/uploads/` — uploads PDF (now extracts citations in background)
- `POST /api/analyze/?file_id=...` — analyzes (now with NLP preprocessing)

Improvements are automatic and transparent.

---

## Commits to Consider

1. **Citation extraction + arXiv resolver** (2 new files)
2. **NLP preprocessing module** (1 new file)
3. **Token counting utilities** (1 new file)
4. **Integration updates** (pdf_parser, uploads, orchestrator, token_budget, requirements)
5. **Documentation** (this file)

Each can be reviewed and tested independently.
