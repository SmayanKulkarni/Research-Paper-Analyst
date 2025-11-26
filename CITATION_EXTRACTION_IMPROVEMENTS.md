# Citation Extraction Improvements

## Problem
Citations were being extracted but then immediately filtered to zero:
```
[2025-11-26 08:34:58,145] [INFO] Extracted 1 citations from text
[2025-11-26 08:34:58,145] [INFO] Filtered 1 citations down to 0 with arXiv identifiers
```

This meant:
- ✅ Citation extraction was finding references
- ❌ But they were all being filtered out as "not arXiv-linkable"

## Root Causes

### Issue 1: Overly Restrictive Citation Extraction
**File:** `backend/app/services/citation_extractor.py`

**Problem:** Only looked for a formal "References" section at the start, then expected `[1] Citation Text` format.

**Reasons citations were missed:**
- Papers without explicit "References" header → zero extraction
- Papers with "Related Work" instead of "References" → missed
- Inline citations scattered through text → not captured
- arXiv/DOI URLs in footnotes or sidebars → ignored

### Issue 2: Overly Restrictive Filtering
**File:** `backend/app/services/citation_extractor.py` → `filter_arxiv_citations()`

**Problem:** Only kept citations with explicit arXiv IDs or arXiv URLs.

**Reasons papers were filtered out:**
- Citations with only DOI links → rejected (no arXiv ID)
- Citations with URLs but no arXiv → rejected
- Missing fallback strategies

### Issue 3: No DOI Resolution
**File:** `backend/app/services/arxiv_finder.py`

**Problem:** Even if DOI citations were kept, they couldn't be resolved.

**Fix:** Added DOI search capability to arXiv.

## Solutions Implemented

### 1. ✅ Multi-Strategy Citation Extraction

**Strategy 1: References Section** (Most Reliable)
- Detects: "References", "Bibliography", "Related Work" sections
- Extracts: `[1] Citation Text` or `1. Citation Text` formats
- Best for: Traditional academic papers

**Strategy 2: Inline Citations** (Fallback)
- Detects: `[NUM]` markers throughout the text
- Extracts: Context around the marker (200 chars before/after)
- Best for: Papers where citations aren't in a single section

**Strategy 3: Standalone URLs** (Last Resort)
- Detects: Standalone `https://arxiv.org/abs/XXXX` or `https://doi.org/XXXX`
- Extracts: URL + metadata
- Best for: Non-standard formatting or URLs in footnotes

### 2. ✅ Improved Filtering Logic

Now keeps citations with **any** of:
- Explicit arXiv IDs (`arXiv:2101.12345`)
- arXiv URLs (`https://arxiv.org/abs/2101.12345`)
- DOI URLs (`https://doi.org/10.XXXX/YYYY`)
- Explicit DOI field

Removed the harsh filtering that was rejecting valid citations.

### 3. ✅ Added DOI Resolution

**File:** `backend/app/services/arxiv_finder.py` → `resolve_citation_to_arxiv()`

Added step to search arXiv by DOI:
```python
if citation.get("doi"):
    search = arxiv.Search(query=f"doi:{doi}", max_results=1)
    # Returns matching paper if found
```

This handles papers that exist on both DOI registries and arXiv.

## Changes Made

### `backend/app/services/citation_extractor.py`

**`extract_citations_from_text()`** - Rewrote with 3-strategy approach:
```python
# STRATEGY 1: Find References/Bibliography section
# STRATEGY 2: If no References, extract inline [NUM] citations
# STRATEGY 3: If no inline citations, find standalone arXiv/DOI URLs
```

**`filter_arxiv_citations()`** - More lenient filtering:
```python
# Keep if: arxiv_id OR arxiv_url OR doi_url OR doi_field
# Previously: Only kept arxiv_id or arxiv_url
```

### `backend/app/services/arxiv_finder.py`

**`resolve_citation_to_arxiv()`** - Added DOI search:
```python
# 1. Try direct arXiv ID
# 2. Try URL-based lookup
# 3. Try DOI search (NEW)
# 4. Try title/author search
```

## Expected Improvements

### Before
```
Extracted 1 citations from text
Filtered 1 citations down to 0 with arXiv identifiers
Result: ❌ No papers ingested
```

### After
```
Extracted 5 citations from text          # Catches inline [1], [2], etc.
Filtered 5 citations down to 3 with arXiv/DOI identifiers  # Keeps DOI+URL+arXiv
Result: ✅ 3 papers resolved and ingested
```

## Citation Format Examples Now Supported

### ✅ Inline [NUM] Citations
```
This builds on [1] prior work...
The key insight [2] shows that...

[1] Smith et al., arXiv:2101.12345
[2] Johnson, https://doi.org/10.1234/test
```

### ✅ Traditional References Section
```
References
[1] Author et al., "Title", arXiv:2101.12345, 2021
[2] Other, "Paper", Journal Name, 2020
```

### ✅ Related Work Section
```
Related Work
[1] Smith et al., arXiv:2202.54321
[2] Brown, https://arxiv.org/pdf/2303.08774.pdf
```

### ✅ Numbered Lists
```
References
1. Smith et al., arXiv:2101.12345
2. Johnson, DOI:10.1234/test
```

### ✅ Standalone URLs
```
(mentions multiple papers including)
https://arxiv.org/abs/2303.08774
https://doi.org/10.1234/nature.2023
```

## Testing

Run the test script to verify extraction:
```bash
cd /home/smayan/Desktop/Research-Paper-Analyst/backend
python3 ../test_citation_extraction.py
```

This will show:
- How many citations are extracted per strategy
- How many pass the arXiv/DOI filter
- What identifiers each citation has

## Files Modified

1. **`backend/app/services/citation_extractor.py`**
   - Rewrote `extract_citations_from_text()` with 3 strategies
   - Improved `filter_arxiv_citations()` to be more lenient
   - Added better logging at each stage

2. **`backend/app/services/arxiv_finder.py`**
   - Enhanced `resolve_citation_to_arxiv()` with DOI search
   - Added DOI resolution via arXiv query

## Next Steps

1. **Test on real papers:** Upload a paper and check if citations are now extracted
2. **Monitor resolution:** Check how many citations resolve vs. fail
3. **Iterate on patterns:** If specific formats still fail, add more patterns
4. **Optional: Enhance title-based search** if many citations still can't be resolved

## Key Insight

The system now catches citations in 3 different ways:
1. **Best case:** Formal references section → most reliable
2. **Middle case:** Inline citations throughout text → more papers caught
3. **Fallback:** Standalone URLs → catches everything else

This multi-strategy approach means that papers with non-standard formatting will still have their citations extracted and resolved.
