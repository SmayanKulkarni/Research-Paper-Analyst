# Embeddings Usage & Expansion Opportunities

## Current State: What Embeddings Are Being Used For

### 1. **Paper Similarity Search (Primary Use Case)**
**File**: `backend/app/services/paper_discovery.py`
**Flow**:
- Extract abstract from an uploaded research paper
- Encode target abstract → dense vector (1024 dimensions)
- Search ArXiv for similar papers in a category
- Encode candidate abstracts → dense vectors
- Compute cosine similarity between target and candidates
- Return top K most similar papers
- Download PDFs and store embeddings in Parquet

**Current Configuration**:
- Model: `BAAI/bge-large-en` (1024-dim embeddings)
- Storage: Local Parquet database with embedding vectors
- Backend: Pinecone (hybrid search capable but not fully utilized)
- Use case: Related work discovery, literature review automation

**Limitations**:
- Only abstracts are embedded (not full paper content)
- Similarity based purely on semantic relevance
- No section-level granularity
- Single embedding per paper (not per-section)

---

### 2. **Vector Database Infrastructure (Partially Utilized)**
**File**: `backend/app/services/pinecone_client.py`
**Current Features**:
- Pinecone index creation and management
- Hybrid search support (dense + sparse vectors)
- Batch upsert operations
- Metadata storage capability

**Current Limitations**:
- Hybrid search API exists but is never called
- Sparse vectors never populated or used
- Metadata fields defined but underutilized
- No retrieval augmentation system
- No semantic caching

---

## Current Architecture Diagram

```
┌─────────────────────────────────────────┐
│   Upload Research Paper                  │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│  Extract Abstract from PDF              │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│  Encode → Dense Vector (1024-dim)      │
│  Model: BAAI/bge-large-en              │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│  Search ArXiv for Similar Papers        │
│  (200 candidates max)                   │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│  Encode Candidate Abstracts             │
│  → Dense Vectors                        │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│  Cosine Similarity Search               │
│  Return Top K Results                   │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│  Download + Store to Parquet            │
│  (title, summary, url, embedding)       │
└─────────────────────────────────────────┘
```

---

## Expansion Opportunities: 10+ New Use Cases

### **TIER 1: High Impact, Low Effort** ⚡

#### 1. **Semantic Section Retrieval**
**Problem**: When analyzing a paper, agents need specific sections (methodology, results, etc.)
**Solution**: 
- Chunk paper into sections (intro, methodology, experiments, etc.)
- Embed each section separately
- When agent runs, retrieve most relevant sections for that task
- Reduces token usage by 70-80% (preprocessor + embedding retrieval)

**Implementation**:
```python
# In paper_preprocessor.py
def embed_and_retrieve_sections(full_text: str, query: str, top_k: int = 3):
    """
    Embed paper sections, retrieve most relevant for agent
    """
    sections = extract_all_sections(full_text)
    section_embeddings = embed_texts([s.content for s in sections])
    query_embedding = embed_texts([query])[0]
    
    similarities = cosine_similarity([query_embedding], section_embeddings)[0]
    top_indices = np.argsort(similarities)[::-1][:top_k]
    
    return [sections[i] for i in top_indices]
```

**Benefits**: 
- ✅ 70-80% token reduction for agents
- ✅ Faster analysis (less input)
- ✅ More focused agent outputs
- ✅ Works with existing preprocessor

**Effort**: 4-6 hours

---

#### 2. **Citation Context Embedding**
**Problem**: Citation verification requires understanding the context around citations
**Solution**:
- Embed citation + surrounding sentence (context window)
- Store citation embeddings in Pinecone
- Enable semantic citation matching (find similar citations across papers)
- Better plagiarism detection

**Implementation**:
```python
# In citation_tool.py
def embed_citations_with_context(full_text: str):
    """
    Extract citations and embed with surrounding context
    """
    citations = extract_all_citations(full_text)
    contexts = []
    
    for citation in citations:
        # Get +/- 2 sentences around citation
        context_window = get_context_window(full_text, citation.position, 2)
        embedding = embed_texts([context_window])[0]
        contexts.append({
            "citation_id": citation.id,
            "citation_text": citation.text,
            "context": context_window,
            "embedding": embedding
        })
    
    return contexts
```

**Benefits**:
- ✅ Better plagiarism detection
- ✅ Citation consistency verification
- ✅ Find similar citations across papers
- ✅ Detect improperly paraphrased citations

**Effort**: 3-4 hours

---

#### 3. **Mathematical Expression Embedding**
**Problem**: Math verification agent can't easily compare equations across papers
**Solution**:
- Extract LaTeX equations
- Normalize mathematical expressions
- Embed normalized forms
- Find semantically equivalent equations (even if different notation)

**Implementation**:
```python
# In math_agent.py services
def embed_math_expressions(full_text: str):
    """
    Extract and embed mathematical expressions
    """
    equations = extract_latex_equations(full_text)
    
    for eq in equations:
        # Normalize notation
        normalized = normalize_math_notation(eq.latex)
        # Create semantic representation
        description = generate_math_description(normalized)
        embedding = embed_texts([description])[0]
        
        equations.append({
            "original": eq.latex,
            "normalized": normalized,
            "description": description,
            "embedding": embedding
        })
    
    return equations
```

**Benefits**:
- ✅ Compare equations across papers
- ✅ Detect equivalent (but differently written) proofs
- ✅ Find mathematical pattern reuse
- ✅ Better consistency verification

**Effort**: 5-7 hours

---

#### 4. **Figure Caption Embedding + Matching**
**Problem**: Vision agent analyzes figures but can't compare figures across papers
**Solution**:
- Extract figure captions
- Embed captions + figure content
- Find similar figures across paper database
- Detect potentially reused/similar figures

**Implementation**:
```python
# In vision_tool.py
def embed_figure_metadata(full_text: str, extracted_images: List):
    """
    Embed figure captions and link to visual content
    """
    figures = []
    
    for image_path in extracted_images:
        # Get associated caption
        caption = find_figure_caption(full_text, image_path)
        
        # Embed caption
        caption_embedding = embed_texts([caption])[0]
        
        # Could also embed image directly if vision model available
        figures.append({
            "image_path": image_path,
            "caption": caption,
            "caption_embedding": caption_embedding,
            "similar_figures": find_similar_figures(caption_embedding)
        })
    
    return figures
```

**Benefits**:
- ✅ Find papers with similar experimental setups
- ✅ Detect reused figures
- ✅ Compare methodologies visually
- ✅ Better literature understanding

**Effort**: 4-5 hours

---

### **TIER 2: Medium Impact, Medium Effort** 🚀

#### 5. **Semantic Paper Recommendation System**
**Problem**: Users don't know what related papers exist in their corpus
**Solution**:
- Embed all papers in Parquet database
- Create recommendation API: "What other papers should I read?"
- Implement collaborative filtering (similar papers → similar users)
- Recommend based on current paper + user reading history

**Implementation**:
```python
# New endpoint: /recommendations/{paper_id}
def get_paper_recommendations(paper_id: str, top_k: int = 10):
    """
    Find semantically similar papers from corpus
    """
    paper = get_paper_from_parquet(paper_id)
    paper_embedding = paper["embedding"]
    
    # Query Pinecone for similar papers
    similar = pinecone_service.query_hybrid(
        dense_vector=paper_embedding,
        top_k=top_k
    )
    
    return format_recommendations(similar)
```

**Benefits**:
- ✅ Improved literature discovery
- ✅ Faster research context building
- ✅ Personalized recommendations
- ✅ Network effect (papers → users → papers)

**Effort**: 8-12 hours (includes API, frontend)

---

#### 6. **Claim & Result Embedding (Evidence Detection)**
**Problem**: Hard to track which papers prove/disprove claims
**Solution**:
- Extract claims and results from papers
- Embed claims semantically
- Create claim-to-evidence mapping
- Find papers supporting/contradicting claims

**Implementation**:
```python
# In clarity_agent services
def embed_claims_and_results(full_text: str):
    """
    Extract and embed key claims + results
    """
    claims = extract_claims(full_text)
    results = extract_key_results(full_text)
    
    embedded_claims = []
    
    for claim in claims:
        # Embed claim text
        embedding = embed_texts([claim.text])[0]
        
        # Find supporting results
        supporting = find_supporting_results(claim, results)
        
        embedded_claims.append({
            "claim": claim.text,
            "claim_embedding": embedding,
            "supporting_results": supporting,
            "evidence_strength": calculate_support_strength(claim, supporting)
        })
    
    return embedded_claims
```

**Benefits**:
- ✅ Systematic evidence tracking
- ✅ Claim verification
- ✅ Contradiction detection
- ✅ Research narrative building

**Effort**: 10-14 hours

---

#### 7. **Author/Institution Clustering**
**Problem**: Can't easily see research communities and collaborations
**Solution**:
- Extract author names and institutions
- Embed author metadata + paper abstracts
- Cluster similar research communities
- Identify research trends by institution

**Implementation**:
```python
def cluster_authors_by_research():
    """
    Find research communities based on papers
    """
    papers = load_all_papers()
    
    # Group by author
    author_papers = {}
    for paper in papers:
        authors = extract_authors(paper)
        for author in authors:
            if author not in author_papers:
                author_papers[author] = []
            author_papers[author].append(paper)
    
    # Embed author research profile
    author_embeddings = {}
    for author, papers in author_papers.items():
        # Average embeddings of all papers
        avg_embedding = np.mean([p["embedding"] for p in papers], axis=0)
        author_embeddings[author] = avg_embedding
    
    # Cluster authors
    clusters = cluster_vectors(author_embeddings)
    return clusters
```

**Benefits**:
- ✅ Research community discovery
- ✅ Collaboration opportunities
- ✅ Research trend identification
- ✅ Field segmentation

**Effort**: 8-10 hours

---

### **TIER 3: Strategic Features** 🎯

#### 8. **Retrieval Augmented Generation (RAG) for Analysis**
**Problem**: Agents analyze papers in isolation without context
**Solution**:
- When analyzing a paper, retrieve similar papers from corpus
- Provide similar papers as context to agents
- Enable comparative analysis
- Better cross-paper insights

**Implementation**:
```python
# In orchestrator.py
def run_analysis_with_rag(pdf_path: str):
    """
    Augment analysis with similar papers for context
    """
    full_text = parse_pdf(pdf_path)
    
    # Get abstract
    abstract = extract_abstract(full_text)
    abstract_embedding = embed_texts([abstract])[0]
    
    # Find similar papers for context
    similar_papers = pinecone_service.query_hybrid(
        dense_vector=abstract_embedding,
        top_k=5
    )
    
    # Create context string
    rag_context = format_similar_papers_for_agents(similar_papers)
    
    # Pass to agents
    for agent_name, agent in agents.items():
        agent_input = f"{full_text}\n\nRELATED WORK CONTEXT:\n{rag_context}"
        run_agent(agent, agent_input)
```

**Benefits**:
- ✅ Better comparative analysis
- ✅ Automatic literature review integration
- ✅ More informed agent decisions
- ✅ Cross-paper consistency detection

**Effort**: 12-16 hours

---

#### 9. **Duplicate & Plagiarism Detection at Scale**
**Problem**: Current plagiarism detection is paper-specific
**Solution**:
- Embed all papers in corpus
- Use embedding similarity to pre-filter potential plagiarism
- Compare suspicious pairs at detail level
- Build plagiarism graph across corpus

**Implementation**:
```python
def detect_plagiarism_at_scale():
    """
    Find potential plagiarism across all papers in corpus
    """
    papers = load_all_papers()
    
    plagiarism_graph = defaultdict(list)
    
    for i, paper1 in enumerate(papers):
        # Query for similar papers
        similar = pinecone_service.query_hybrid(
            dense_vector=paper1["embedding"],
            top_k=20
        )
        
        for match in similar:
            if match["score"] > 0.95:  # Very similar
                paper2 = get_paper_by_id(match["id"])
                
                # Detailed plagiarism check
                plagiarism_pct = detailed_plagiarism_check(paper1, paper2)
                
                if plagiarism_pct > 0.3:  # >30% similar
                    plagiarism_graph[paper1["id"]].append({
                        "similar_to": paper2["id"],
                        "similarity": plagiarism_pct
                    })
    
    return plagiarism_graph
```

**Benefits**:
- ✅ System-wide plagiarism detection
- ✅ Faster than pairwise comparison
- ✅ Multi-paper fraud detection
- ✅ Research integrity monitoring

**Effort**: 16-20 hours

---

#### 10. **Semantic Search + Filtering API**
**Problem**: Can't search papers by complex semantic queries
**Solution**:
- Create semantic search API for research corpus
- Support complex filters: "papers about adversarial attacks that use GANs"
- Combine keyword + semantic search (hybrid)
- Return ranked results with explanations

**Implementation**:
```python
@app.post("/search/semantic")
def semantic_search(query: str, filters: Dict = None, top_k: int = 20):
    """
    Semantic search across paper corpus
    Example: "papers on adversarial robustness in neural networks"
    """
    # Embed query
    query_embedding = embed_texts([query])[0]
    
    # Search Pinecone
    results = pinecone_service.query_hybrid(
        dense_vector=query_embedding,
        top_k=top_k
    )
    
    # Apply filters if provided
    filtered = apply_semantic_filters(results, filters)
    
    return format_search_results(filtered)
```

**Benefits**:
- ✅ Powerful research corpus exploration
- ✅ Complex query support
- ✅ Better than keyword search
- ✅ User-friendly API

**Effort**: 14-18 hours

---

#### 11. **Contradiction & Conflicting Evidence Detection**
**Problem**: Can't detect contradictions across papers
**Solution**:
- Embed main claims from each paper
- Compare claims for contradictions
- Find papers with opposing conclusions
- Flag contradictions in analysis reports

**Implementation**:
```python
def find_contradictions_in_corpus():
    """
    Find papers with contradicting claims
    """
    papers = load_all_papers()
    
    contradictions = []
    
    for i in range(len(papers)):
        for j in range(i+1, len(papers)):
            paper1 = papers[i]
            paper2 = papers[j]
            
            # Get claims
            claims1 = extract_claims(paper1)
            claims2 = extract_claims(paper2)
            
            # Compare claim embeddings
            for claim1 in claims1:
                for claim2 in claims2:
                    emb1 = embed_texts([claim1.text])[0]
                    emb2 = embed_texts([claim2.text])[0]
                    
                    similarity = cosine_similarity(emb1, emb2)
                    
                    # Check if semantically similar but opposite conclusions
                    if similarity > 0.7 and are_opposing(claim1, claim2):
                        contradictions.append({
                            "paper1": paper1["id"],
                            "paper2": paper2["id"],
                            "claim1": claim1.text,
                            "claim2": claim2.text,
                            "contradiction_score": calculate_contradiction_score(claim1, claim2)
                        })
    
    return contradictions
```

**Benefits**:
- ✅ Detect contradictory research
- ✅ Flag disputed findings
- ✅ Better research context
- ✅ Identify future research opportunities

**Effort**: 12-16 hours

---

#### 12. **Multi-Modal Paper Embedding (Text + Figures + Tables)**
**Problem**: Current embeddings only use text abstracts
**Solution**:
- Embed full text (not just abstract)
- Embed figures (or figure captions)
- Embed table contents
- Create composite multi-modal embeddings
- Better semantic representation

**Implementation**:
```python
def create_multimodal_paper_embedding(paper_path: str):
    """
    Create composite embedding from multiple paper components
    """
    # Extract components
    full_text = extract_full_text(paper_path)
    abstract = extract_abstract(paper_path)
    figures_captions = extract_figure_captions(paper_path)
    table_contents = extract_table_contents(paper_path)
    
    # Embed each component
    text_emb = embed_texts([full_text])[0]
    abstract_emb = embed_texts([abstract])[0]
    figure_embs = embed_texts(figures_captions)
    table_embs = embed_texts(table_contents)
    
    # Weighted combination
    composite_emb = (
        0.4 * text_emb +           # Full text (most important)
        0.3 * abstract_emb +       # Abstract (concise summary)
        0.2 * np.mean(figure_embs) +  # Figures (methodology/results)
        0.1 * np.mean(table_embs)     # Tables (data)
    )
    
    return composite_emb
```

**Benefits**:
- ✅ Richer semantic representation
- ✅ Better similarity matching
- ✅ Captures more paper context
- ✅ Improved recommendations

**Effort**: 10-12 hours

---

## Implementation Roadmap

### **Phase 1: Foundation (Weeks 1-2)** ⚡ Easy Wins
1. Semantic Section Retrieval (#1)
2. Citation Context Embedding (#2)
3. Figure Caption Embedding (#4)

**Expected Impact**: 
- 60-70% token reduction when combined with preprocessor
- Better plagiarism detection
- Faster agent analysis

**Effort**: 12-15 hours total

---

### **Phase 2: Enhancement (Weeks 3-4)** 🚀 Medium Features
4. Mathematical Expression Embedding (#3)
5. Claim & Result Embedding (#6)
6. Semantic Paper Recommendation (#5)

**Expected Impact**:
- Better verification capabilities
- Recommendation system live
- Community feedback integration

**Effort**: 24-32 hours total

---

### **Phase 3: Scale (Weeks 5-6)** 🎯 Strategic Features
7. Retrieval Augmented Generation (#8)
8. Duplicate Detection at Scale (#9)
9. Semantic Search API (#10)

**Expected Impact**:
- Advanced analysis capabilities
- Corpus-wide insights
- User-facing search features

**Effort**: 42-54 hours total

---

### **Phase 4: Polish (Weeks 7-8)** ✨ Optional
10. Author/Institution Clustering (#7)
11. Contradiction Detection (#11)
12. Multi-Modal Embeddings (#12)

**Expected Impact**:
- Research community features
- Research integrity tools
- Enhanced representations

**Effort**: 30-40 hours total

---

## Technical Prerequisites

### Required Upgrades
1. **Switch embedding model** (if scaling)
   - Current: `BAAI/bge-large-en` (1024-dim, good balance)
   - Consider: `sentence-transformers/all-mpnet-base-v2` (768-dim, faster)
   - Or: `Alibaba-NLP/gte-base-en-v1.5` (768-dim, semantic search optimized)

2. **Expand Pinecone usage**
   - Currently: Upsert vectors but never query
   - Needed: Implement query methods for all use cases
   - Consider: Sparse vector implementation for keyword augmentation

3. **Add semantic caching**
   - Cache embedding computations
   - Avoid re-embedding identical text
   - Significant speedup for corpus operations

4. **Batch processing**
   - Embed papers in parallel batches
   - Use GPU if available (`SentenceTransformer(..., device='cuda')`)

---

## Quick Start: Implementation Priority

**Start with #1: Semantic Section Retrieval**
- Combines perfectly with existing preprocessor
- Immediate token/cost reduction (60-70%)
- Improves agent outputs
- ~4-6 hours to implement

**Then add #2: Citation Context Embedding**
- Enhances plagiarism detection
- Works with existing citation tool
- ~3-4 hours

**Then #4: Figure Caption Embedding**
- Extends vision agent capabilities
- ~4-5 hours

These three together create a comprehensive foundation for all other features.

---

## Potential Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| Embedding computation cost | Batch process, cache, use smaller model |
| Storage size (1000s of papers × 1024-dim vectors) | Compress vectors, use quantization, cloud storage |
| Similarity threshold tuning | Start conservative (0.8), adjust based on results |
| Semantic drift over time | Periodically re-embed to catch model updates |
| Real-time search latency | Implement caching, index optimization |

---

## Success Metrics

After implementing these features, track:
1. **Token usage reduction** (target: 60-80% from baseline)
2. **Analysis quality** (measure improvement in agent outputs)
3. **User engagement** (recommendations, searches per user)
4. **Accuracy of detection** (plagiarism, contradictions)
5. **Search relevance** (user satisfaction with results)

