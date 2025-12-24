# Embeddings Quick Reference Guide

## Current Usage Summary

### What's Being Used Now
✅ **Dense embeddings** (1024-dim vectors using BAAI/bge-large-en)
✅ **Paper abstracts** → encoded for similarity search
✅ **ArXiv paper discovery** → find related papers
✅ **Parquet storage** → local database of papers + embeddings
✅ **Pinecone backend** → ready but underutilized

### What's NOT Being Used (Despite Infrastructure)
❌ **Hybrid search** (dense + sparse) — API exists but never called
❌ **Section-level embeddings** — only abstract-level
❌ **Semantic retrieval in analysis** — agents don't use embeddings
❌ **Citation embeddings** — embeddings don't help with citation analysis
❌ **Mathematical embeddings** — math agent doesn't use embeddings
❌ **Figure embeddings** — vision agent doesn't use embeddings
❌ **Semantic search API** — no endpoint for users
❌ **Recommendation system** — no suggestions for users
❌ **Corpus-wide analysis** — no cross-paper insights

---

## Quick Wins: Highest ROI Features

### 1️⃣ Semantic Section Retrieval (4-6 hours)
**Impact**: 60-70% token reduction + faster analysis
```
Input: Full paper (50k tokens)
↓
Extract & embed sections
↓
For Language Agent: Return abstract + intro + conclusion (15k tokens)
For Citation Agent: Return citations + references (5k tokens)
For Math Agent: Return equations + theorems (2k tokens)
↓
Output: Agents get exactly what they need, less waste
```

### 2️⃣ Citation Context Embedding (3-4 hours)
**Impact**: Better plagiarism detection
```
Extract: [1] + surrounding 2 sentences
↓
Embed: Context window as semantic vector
↓
Store: In Pinecone for corpus-wide matching
↓
Query: Find similar citations in other papers
→ Detects: Improperly paraphrased citations, hidden plagiarism
```

### 3️⃣ Figure Caption Embedding (4-5 hours)
**Impact**: Find similar experimental setups
```
Extract: Figure captions from all papers
↓
Embed: Caption text + image metadata
↓
Query: Find papers with similar experimental methods
↓
Use: Recommend papers with similar figures, detect figure reuse
```

**Total Quick Win Time**: ~12-15 hours → Major capability boost

---

## Feature Matrix: Impact vs Effort

```
HIGH IMPACT
    ▲
    │
    │  [8]RAG        [9]Plagiarism    [10]Search
    │  Analysis      at Scale         API
    │    ●              ●              ●
    │              [5]Recommend
    │         [6]Claims        [7]Author
    │            ●            Clustering ●
    │         [3]Math          [11]Contradictions
    │  [1]Section   ●              ●
    │  Retrieval    [2]Citation    [12]MultiModal
    │     ●         Context ●        ●
    │         [4]Figure ●
    │
    └─────────────────────────────────────────→ EFFORT
    LOW                                        HIGH
```

---

## Where Embeddings Should Be Used

```
Current Paper Analysis Pipeline:
┌──────────────┐
│   PDF Input  │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  MISSING: Embedding-based retrieval for agents      │
│  7 specialized agents analyze FULL paper            │
│  (Could use embeddings to give each agent only      │
│   the sections it needs)                            │
└──────────────┬───────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  Language Quality Agent                              │
│  Structure Agent                                     │
│  Citation Agent                                      │
│  Clarity Agent                                       │
│  Flow Agent                                          │
│  Math Agent                                          │
│  Vision Agent                                        │
└──────────────┬───────────────────────────────────────┘
       │
       ▼
┌──────────────┐
│ PDF Report   │
└──────────────┘


ENHANCED Pipeline with Embeddings:
┌──────────────┐
│   PDF Input  │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  Extract sections + create embeddings               │
│  Split paper into semantic chunks                   │
└──────────────┬───────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  For each agent, retrieve relevant sections:        │
│                                                      │
│  Language Quality → Abstract + Writing samples      │
│  Structure → All headings + transitions             │
│  Citation → All citations + references              │
│  Clarity → Claims + reasoning + conclusions         │
│  Flow → Topic sentences + transitions               │
│  Math → Equations + theorems                        │
│  Vision → Figure captions + analysis                │
└──────────────┬───────────────────────────────────────┘
       │
       ▼
┌──────────────┐
│ Agents run with optimized input (60-80% less tokens)
│ Faster execution + Same quality + Lower cost
└──────────────┘
```

---

## Before vs After: Token Comparison

### Example: 15-Page Research Paper

**BEFORE (Current)**:
```
Paper: ~50,000 tokens
├─ Language Agent: 50k tokens
├─ Structure Agent: 50k tokens
├─ Citation Agent: 50k tokens
├─ Clarity Agent: 50k tokens
├─ Flow Agent: 50k tokens
└─ Math Agent: 50k tokens
──────────────────────────
Total: 300,000 tokens used
```

**AFTER (With Embeddings + Semantic Retrieval)**:
```
Paper: ~50,000 tokens
Preprocessing creates semantic chunks
├─ Language Agent: 10k tokens (abstract + intro + conclusion)
├─ Structure Agent: 8k tokens (headings + boundaries)
├─ Citation Agent: 5k tokens (citations + references)
├─ Clarity Agent: 8k tokens (claims + reasoning)
├─ Flow Agent: 7k tokens (transitions + signposts)
└─ Math Agent: 2k tokens (equations + theorems only)
──────────────────────────
Total: 40,000 tokens used
──────────────────────────
Savings: 86% reduction (300k → 40k)
Cost: 1/7.5 of original
Speed: ~3x faster (less input = faster LLM processing)
```

---

## Implementation Checklist: Phase 1 (Quick Wins)

### Feature #1: Semantic Section Retrieval
- [ ] Modify `paper_preprocessor.py` to create section embeddings
- [ ] Add `embed_and_retrieve_sections()` method
- [ ] Integrate into orchestrator's preprocessing phase
- [ ] Pass retrieved sections to each agent instead of full text
- [ ] Test on sample papers, measure token reduction
- [ ] Update documentation

**Estimated Time**: 4-6 hours
**Expected Gain**: 60-70% token reduction

---

### Feature #2: Citation Context Embedding
- [ ] Extract citations with context windows (±2 sentences)
- [ ] Create embeddings for citation contexts
- [ ] Store in Pinecone with citation metadata
- [ ] Build citation similarity search
- [ ] Integrate into citation_agent for comparison
- [ ] Test with sample papers

**Estimated Time**: 3-4 hours
**Expected Gain**: Better plagiarism detection, citation verification

---

### Feature #3: Figure Caption Embedding
- [ ] Extract figure captions from PDFs
- [ ] Create embeddings for captions
- [ ] Implement figure similarity search
- [ ] Find papers with similar figures
- [ ] Display in vision agent output
- [ ] Test with image-heavy papers

**Estimated Time**: 4-5 hours
**Expected Gain**: Find related experimental work, detect figure reuse

---

## Code Files to Modify

```
Key Files for Phase 1:

1. backend/app/services/paper_preprocessor.py
   ├─ Add: embed_and_retrieve_sections()
   └─ Add: get_section_embeddings()

2. backend/app/crew/orchestrator.py
   ├─ Import: embed_and_retrieve_sections
   └─ Modify: preprocessing phase to use embeddings

3. backend/app/services/embeddings.py
   ├─ Already exists - no changes needed
   └─ Already has embed_texts() function

4. backend/app/services/pinecone_client.py
   ├─ Add: query_sections()
   └─ Already has infrastructure

5. backend/app/crew/agents/*.py (if needed)
   └─ Agents already flexible with input changes
```

---

## Expected Outcomes

### After Phase 1 (Quick Wins):
✅ 60-70% token reduction per analysis
✅ ~3x faster paper analysis
✅ Better plagiarism detection
✅ Improved agent outputs (cleaner input)
✅ Lower API costs
✅ Foundation for advanced features

### By End of All Phases:
✅ Comprehensive retrieval system (RAG)
✅ Recommendation engine
✅ Advanced search API
✅ Corpus-wide insights
✅ Research integrity tools
✅ Community detection

---

## Next Steps

1. **Review this document** with the team
2. **Prioritize Phase 1** features (Quick Wins)
3. **Estimate effort** more precisely with your team
4. **Start implementation** with Feature #1 (Semantic Section Retrieval)
5. **Measure results** (token reduction, quality)
6. **Iterate** based on results

---

## Questions to Consider

1. **Which feature would help users most?**
   - Recommendations? Search? Analysis quality?

2. **What's the priority: speed or cost?**
   - Embeddings help with both (less tokens = faster + cheaper)

3. **Do we need real-time capabilities?**
   - Or can we batch-process embeddings?

4. **Should we expand beyond abstract embeddings?**
   - Full-text embeddings = more context but more compute

5. **Which agent would benefit most?**
   - Citation agent (for verification)
   - Math agent (for comparison)
   - All agents (for efficiency)

