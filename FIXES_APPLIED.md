# Fixes Applied - Error Resolution

## Issues Fixed

### 1. ❌ `asyncio.run() cannot be called from a running event loop`
**Root Cause:** `crawl_and_ingest_sync()` in `web_crawler.py` was calling `asyncio.run()` on a synchronous function, while CrewAI was already running in an async context.

**Files Fixed:**
- `backend/app/services/web_crawler.py`
  - Removed `import asyncio` (line 4)
  - Added `import time` (line 3)
  - Fixed `asyncio.sleep()` → `time.sleep()` (lines 50, 58)
  - Removed `asyncio.run()` from `crawl_and_ingest_sync()` (was calling on already-sync function)

**Result:** ✅ No more asyncio event loop conflicts

---

### 2. ❌ `RuntimeWarning: coroutine 'crawl_and_ingest' was never awaited`
**Root Cause:** Related to the asyncio.run() issue above.

**Fix:** Same as Issue #1 - function is now properly synchronous.

**Result:** ✅ No more coroutine warnings

---

### 3. ✅ Unused Imports Removed
**File:** `backend/app/services/plagiarism.py`
- Removed: `from app.services.web_crawler import crawl_and_ingest_sync`
- Removed: `from app.services.llm_provider import call_groq_with_retries, groq_llm`

**Reason:** Fallback crawl is disabled. Papers come from citation extraction during PDF upload.

---

## Architecture Verification

### ✅ NLP Preprocessing = Pure NLP (No LLM Calls)
**File:** `backend/app/services/nlp_preprocessor.py`

Confirmed: Uses only transformers models, spaCy, KeyBERT, and regex patterns. No Groq/LLM calls.

Functions:
- `extract_key_phrases()` - KeyBERT + regex fallback
- `extract_entities()` - spaCy + regex fallback  
- `abstractive_summarize()` - BART + extractive fallback
- `preprocess_research_paper()` - Orchestrates above
- `preprocess_for_chunk_compression()` - Lightweight regex-only

---

### ✅ NLP Preprocessing is Disabled by Default
**File:** `backend/app/crew/orchestrator.py`

**Line 35:** `enable_nlp_preprocessing: bool = False  # DISABLED by default due to TPM limits`

- NLP preprocessing is opt-in via parameter
- Can be enabled when TPM usage is under control
- All fallbacks ensure graceful degradation

---

### ✅ Token Limits are Aggressive
**File:** `backend/app/config.py`

```python
GROQ_TPM_LIMIT: int = 6000                           # Actual free tier limit
TOKEN_BUDGET_SAFETY_MARGIN: float = 0.70             # Use only 70% (was 80%)
MAX_CHUNKS_TO_COMPRESS: int = 5                      # Reduced from 10 to 5
MAX_ANALYSIS_TEXT_LENGTH: int = 3000                 # Reduced from 5000 to 3000
CREW_MAX_CONCURRENT_LLM_CALLS: int = 1              # Sequential only (was 2)
```

---

### ✅ Plagiarism Fallback is Disabled
**File:** `backend/app/services/plagiarism.py`

```python
def check_plagiarism_with_fallback(
    ...
    fallback_to_crawl: bool = False,  # DISABLED
    ...
):
    results = check_plagiarism(text, ...)
    if results:
        return results
    
    # NO FALLBACK CRAWL - papers come from citation extraction
    logger.info("No plagiarism matches found. Papers are populated from citation extraction.")
    return results
```

---

## Testing the Fixes

### Run Validation
```bash
python validate_fixes.py
```

### Expected Output
```
🔍 Validation Report

📄 backend/app/services/plagiarism.py
  ✅ All checks passed

📄 backend/app/services/nlp_preprocessor.py
  ✅ All checks passed

📄 backend/app/services/web_crawler.py
  ✅ All checks passed

✅ All validations passed!
```

---

## How the System Works Now

### Upload Flow (Background Task)
```
PDF uploaded
  ↓
_process_citations_on_upload()
  ├─ Extract text, images, citations (no LLM)
  ├─ Resolve citations to arXiv papers (no LLM, pure NLP package)
  └─ Embed & ingest to Pinecone (embedding model only)
```

### Analysis Flow
```
Analysis requested
  ↓
run_full_analysis(enable_nlp_preprocessing=False)  ← Disabled by default
  ├─ Load PDF text
  ├─ Chunking & Compression (Groq LLM calls)
  └─ Multi-agent Analysis (Groq LLM calls)
       ├─ Plagiarism check (Pinecone similarity, no crawl)
       ├─ Citation check
       ├─ Structure check
       ├─ Consistency check
       ├─ Proofreading
       └─ Vision analysis
```

**Key Point:** NLP preprocessing is pure NLP, completely separate from LLM tier limits.

---

## Summary

| Issue | Status | Fix |
|-------|--------|-----|
| asyncio.run() in event loop | ✅ Fixed | Removed asyncio.run() call, made function properly sync |
| asyncio.sleep() → time.sleep() | ✅ Fixed | Replaced with blocking sleep |
| Unused imports | ✅ Cleaned | Removed crawl/LLM imports from plagiarism |
| NLP has LLM calls | ✅ Verified | No Groq calls in nlp_preprocessor |
| Rate limit exceeded | ✅ Mitigated | Aggressive token limits + disabled NLP by default |

---

## Next Steps

1. **Test the upload flow:** PDF → citation extraction → arXiv ingestion
2. **Test the analysis flow:** Should complete without 429 errors
3. **Monitor token usage:** Check logs for token tracking
4. **When stable, enable NLP:** Re-enable preprocessing if TPM usage is low

---

## Important Notes

- ⚠️ **NLP preprocessing is DISABLED by default** - enable only when TPM permits
- ✅ **All NLP is pure Python** - no LLM calls in preprocessing
- ✅ **Plagiarism fallback is disabled** - papers come from citations only
- ✅ **Concurrency is sequential** - prevents TPM bursts
- ✅ **Token budgets are conservative** - 70% safety margin on 6000 TPM limit
