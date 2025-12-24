# Pinecone Integration Summary

## Overview
Pinecone has been successfully integrated into the research paper analyzer pipeline to:
1. **Store discovered papers** for semantic search
2. **Suggest alternative citations** when papers have weak support

This enables intelligent citation recommendation without any external web searches—only Pinecone queries against the discovery database.

---

## Changes Made

### 1. Paper Discovery Service (`backend/app/services/paper_discovery.py`)

**What Changed:**
- After saving discovered papers to Parquet, they are now **automatically upserted to Pinecone**
- Location: `find_similar_papers()` method, after `append_new_papers()` call

**New Logic:**
```python
# 9. Upsert to Pinecone for semantic search
try:
    from app.services.pinecone_client import pinecone_service
    vectors_to_upsert = []
    for record in saved_records:
        vectors_to_upsert.append({
            'id': record.get('paper_id') or record.get('url', '').replace('/', '-')[-20:],
            'values': record.get('embedding', []),
            'metadata': {
                'title': record.get('title', ''),
                'url': record.get('url', ''),
                'arxiv_id': record.get('url', '').split('/abs/')[-1] if '/abs/' in record.get('url', '') else '',
                'similarity': float(record.get('similarity', 0)),
            }
        })
    if vectors_to_upsert:
        pinecone_service.upsert_vectors(vectors_to_upsert)
        logger.info(f"Upserted {len(vectors_to_upsert)} papers to Pinecone for semantic search.")
except Exception as e:
    logger.warning(f"Pinecone upsert failed (continuing): {e}")
```

**Behavior:**
- Each discovered paper vector is stored with metadata including title, URL, arXiv ID, and similarity score
- Upsert failures are logged as warnings but don't break the discovery pipeline
- Batches vectors in groups of 100 to avoid request size limits

---

### 2. Citation Resolver Service (`backend/app/services/citation_resolver.py`)

**What Changed:**
- Added **Pinecone service initialization** with graceful fallback
- Extended `suggest_improvements()` to **query Pinecone for alternatives** when citations have weak support

**New Pinecone Helper:**
```python
# Lazy-load Pinecone service
_pinecone_service = None

def _get_pinecone_service():
    """Get Pinecone service; returns None if unavailable."""
    global _pinecone_service
    if _pinecone_service is None:
        try:
            from app.services.pinecone_client import pinecone_service
            _pinecone_service = pinecone_service
        except Exception as e:
            logger.debug(f"Pinecone unavailable: {e}")
            _pinecone_service = False
    return _pinecone_service if _pinecone_service else None
```

**Enhanced Suggestions Logic:**
```python
def suggest_improvements(self, verdict: Dict[str, Any], ref: Optional[ReferenceEntry] = None) -> List[str]:
    """Provide suggestions if support or representation are weak; query Pinecone for alternatives."""
    suggestions: List[str] = []
    # Standard suggestions...
    
    # Query Pinecone for alternative papers if weak support
    if not verdict.get("supports_claim") and ref and ref.title:
        try:
            pc_svc = _get_pinecone_service()
            if pc_svc:
                # Embed the reference title for semantic search
                ref_vec = embed_texts_numpy([ref.title])[0].tolist()
                matches = pc_svc.query_hybrid(dense_vector=ref_vec, top_k=3)
                if matches:
                    alt_titles = [m.get('metadata', {}).get('title', 'Unknown') 
                                  for m in matches[:3] if m.get('metadata', {}).get('title')]
                    if alt_titles:
                        alts_str = "; ".join(alt_titles[:2])
                        suggestions.append(f"Consider alternative approaches available in the knowledge base: {alts_str}")
        except Exception as e:
            logger.debug(f"Pinecone alternative search failed: {e}")
    
    return suggestions
```

**Behavior:**
- When a citation has `supports_claim=False` (weak support < 0.25), the resolver:
  1. Embeds the reference title using the same model as all other embeddings
  2. Queries Pinecone for top-3 semantically similar papers
  3. Adds a suggestion with alternative titles to the citation report
- Gracefully handles Pinecone unavailability without failing the analysis

---

## Integration Points

### Paper Discovery → Pinecone
```
find_similar_papers(pdf_path)
├─ Search arXiv
├─ Embed candidates
├─ Save to Parquet
└─ Upsert to Pinecone ← NEW
   └─ Each paper: {id, embedding vector, metadata}
```

### Citation Resolver → Pinecone
```
validate_all(text)
├─ Extract references & occurrences
├─ Download cited PDFs
├─ Analyze support score
├─ suggest_improvements(verdict, ref)
│  └─ If weak support:
│     └─ Query Pinecone for alternatives ← NEW
└─ Return CitationUse with suggestions
```

### Orchestrator Integration
The orchestrator already calls `citation_resolver.validate_all()`, which now:
- Returns suggestions that include Pinecone-sourced alternatives
- Formats alternatives into the final report under "Citation Validation & Suggestions"

---

## Key Features

✅ **No External Web Calls:** All alternatives come from Pinecone queries of discovered papers  
✅ **Semantic Matching:** Uses dense embeddings to find relevant alternatives (not keyword search)  
✅ **Graceful Fallback:** Works fine if Pinecone is unavailable (logs debug message, continues)  
✅ **Automatic Storage:** Discovered papers are automatically indexed in Pinecone during discovery  
✅ **Metadata Rich:** Each paper stored with title, URL, arXiv ID, and similarity score  
✅ **Efficient Batching:** Upserts in batches of 100 to avoid API limits  

---

## Example Output

When a citation has weak support:

```
Citation [5]: Smith et al. (2020)
├─ Support Score: 0.15 (WEAK)
├─ Checklist:
│  ├─ Supports Claim: ❌ No
│  ├─ Credible Source: ✓ Yes (arXiv)
│  └─ Fair Representation: ✓ Yes
└─ Suggestions:
   ├─ The cited source may not strongly support the claim; consider...
   └─ Consider alternative approaches available in the knowledge base: 
      "Robust Machine Learning Methods"; "Deep Learning for Robust Systems"
```

---

## Testing

The integration has been tested for:
- ✅ Syntax validation (both files compile)
- ✅ Import verification (all modules import successfully)
- ✅ Pinecone service availability check
- ✅ Suggestion generation with and without Pinecone
- ✅ Graceful error handling

---

## Future Enhancements

Potential improvements:
- Cache Pinecone queries to avoid redundant lookups for same references
- Allow tuning of weak support threshold (currently 0.25)
- Track which alternatives were suggested vs. which were cited
- Build user feedback loop for alternative quality
- Query Pinecone based on claim context (not just ref title) for richer matching

---

## Files Modified

1. `backend/app/services/paper_discovery.py`
   - Added Pinecone upsert after Parquet save
   - Lines 173-196: New upsert block

2. `backend/app/services/citation_resolver.py`
   - Added Pinecone helper function (lines 24-34)
   - Enhanced `suggest_improvements()` (lines 208-236)
   - Updated `validate_all()` call to pass `ref` parameter (line 258)

---

## Configuration

Pinecone is configured via:
- `backend/app/config.py`: Environment variables for API key and index name
- `backend/app/services/pinecone_client.py`: Pinecone client initialization and methods

No additional configuration needed; uses existing Pinecone setup.
