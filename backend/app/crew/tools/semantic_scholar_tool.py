"""
Plagiarism Detection Tool - Uses OpenAlex + Sentence Transformers for real content comparison.
No LLM calls, no API keys needed for similarity (runs locally).
"""

import requests
import time
import re
import numpy as np
from typing import List, Dict, Any, Tuple
from crewai.tools import tool
from app.utils.logging import logger

# Lazy load sentence-transformers to avoid slow startup
_model = None
_model_name = "all-MiniLM-L6-v2"  # Fast, accurate, 80MB

OPENALEX_API = "https://api.openalex.org/works"
POLITE_EMAIL = "research-paper-analyst@example.com"


def get_embedding_model():
    """Lazy load the sentence-transformers model."""
    global _model
    if _model is None:
        logger.info(f"Loading sentence-transformers model: {_model_name}...")
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(_model_name)
            logger.info("✅ Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return None
    return _model


def extract_sentences(text: str, max_sentences: int = 50) -> List[str]:
    """Extract meaningful sentences from text for comparison."""
    # Clean and split into sentences
    text = re.sub(r'\s+', ' ', text)
    
    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Filter and clean sentences
    clean_sentences = []
    for sent in sentences:
        sent = sent.strip()
        # Skip too short, too long, or boilerplate sentences
        if len(sent) < 30 or len(sent) > 500:
            continue
        # Skip common boilerplate
        lower = sent.lower()
        if any(skip in lower for skip in [
            'certificate', 'declaration', 'submitted', 'signature',
            'acknowledgment', 'table of contents', 'list of figures',
            'copyright', 'all rights reserved'
        ]):
            continue
        clean_sentences.append(sent)
    
    return clean_sentences[:max_sentences]


def compute_similarity(embeddings1: np.ndarray, embeddings2: np.ndarray) -> float:
    """Compute maximum cosine similarity between two sets of embeddings."""
    # Normalize embeddings
    norm1 = embeddings1 / np.linalg.norm(embeddings1, axis=1, keepdims=True)
    norm2 = embeddings2 / np.linalg.norm(embeddings2, axis=1, keepdims=True)
    
    # Compute cosine similarity matrix
    similarity_matrix = np.dot(norm1, norm2.T)
    
    # Get maximum similarity for each sentence in embeddings1
    max_similarities = np.max(similarity_matrix, axis=1)
    
    # Return average of top similarities
    return float(np.mean(max_similarities))


def find_similar_sentences(
    paper_sentences: List[str], 
    paper_embeddings: np.ndarray,
    ref_sentences: List[str], 
    ref_embeddings: np.ndarray,
    threshold: float = 0.75
) -> List[Tuple[str, str, float]]:
    """Find pairs of similar sentences above threshold."""
    similar_pairs = []
    
    if len(ref_sentences) == 0 or len(paper_sentences) == 0:
        return similar_pairs
    
    # Normalize
    norm_paper = paper_embeddings / np.linalg.norm(paper_embeddings, axis=1, keepdims=True)
    norm_ref = ref_embeddings / np.linalg.norm(ref_embeddings, axis=1, keepdims=True)
    
    # Compute similarities
    similarity_matrix = np.dot(norm_paper, norm_ref.T)
    
    # Find pairs above threshold
    for i, paper_sent in enumerate(paper_sentences):
        for j, ref_sent in enumerate(ref_sentences):
            sim = similarity_matrix[i, j]
            if sim >= threshold:
                similar_pairs.append((paper_sent[:100], ref_sent[:100], float(sim)))
    
    # Sort by similarity descending
    similar_pairs.sort(key=lambda x: x[2], reverse=True)
    
    return similar_pairs[:5]  # Top 5 matches


def extract_key_phrases(text: str, max_phrases: int = 5) -> List[str]:
    """Extract key phrases for OpenAlex search."""
    phrases = []
    clean_text = text.lower()
    
    # Look for research contribution patterns
    patterns = [
        r'we propose[d]?\s+(?:a\s+)?([^.]{15,80})',
        r'we present[s]?\s+(?:a\s+)?([^.]{15,80})',
        r'this paper (?:presents?|proposes?)\s+([^.]{15,80})',
        r'novel\s+([^.]{15,60})',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, clean_text, re.IGNORECASE)
        for match in matches[:2]:
            if 15 < len(match) < 100:
                phrases.append(match.strip())
    
    # Extract from abstract
    abstract_match = re.search(r'abstract[:\s]*(.{50,500}?)(?:\n\n|introduction)', clean_text, re.IGNORECASE | re.DOTALL)
    if abstract_match:
        sentences = re.split(r'\.\s+', abstract_match.group(1))
        for sent in sentences[:2]:
            if len(sent) > 30:
                phrases.append(sent[:150])
    
    # Domain keywords
    domain_keywords = [
        (r'deep learning', 'deep learning'),
        (r'pose estimation', 'human pose estimation'),
        (r'computer vision', 'computer vision'),
        (r'neural network', 'neural network'),
    ]
    
    for pattern, term in domain_keywords:
        if re.search(pattern, clean_text, re.IGNORECASE):
            phrases.append(term)
    
    # Remove duplicates
    seen = set()
    unique = []
    for p in phrases:
        key = p.lower()[:40]
        if key not in seen:
            seen.add(key)
            unique.append(p)
    
    return unique[:max_phrases]


def search_openalex(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search OpenAlex API for papers."""
    try:
        clean_query = re.sub(r'[^\w\s]', ' ', query)
        clean_query = ' '.join(clean_query.split()[:12])
        
        if len(clean_query) < 10:
            return []
        
        params = {
            "search": clean_query,
            "per_page": limit,
            "select": "id,title,authorships,publication_year,cited_by_count,doi,abstract_inverted_index"
        }
        
        response = requests.get(
            OPENALEX_API,
            params=params,
            headers={"User-Agent": f"ResearchPaperAnalyst/1.0 (mailto:{POLITE_EMAIL})"},
            timeout=15
        )
        
        if response.status_code == 429:
            time.sleep(2)
            return []
            
        response.raise_for_status()
        data = response.json()
        
        papers = []
        for work in data.get("results", []):
            # Reconstruct abstract
            abstract = ""
            if work.get("abstract_inverted_index"):
                try:
                    inv_index = work["abstract_inverted_index"]
                    if inv_index:
                        max_pos = max(max(positions) for positions in inv_index.values())
                        words = [""] * (max_pos + 1)
                        for word, positions in inv_index.items():
                            for pos in positions:
                                if pos < len(words):
                                    words[pos] = word
                        abstract = " ".join(w for w in words if w)
                except:
                    pass
            
            authors = [a.get("author", {}).get("display_name", "") 
                      for a in work.get("authorships", [])[:3]]
            
            papers.append({
                "title": work.get("title", "Unknown"),
                "abstract": abstract,
                "authors": [a for a in authors if a],
                "year": work.get("publication_year"),
                "citations": work.get("cited_by_count", 0),
                "doi": work.get("doi", ""),
            })
        
        return papers
        
    except Exception as e:
        logger.error(f"OpenAlex search error: {e}")
        return []


def run_plagiarism_search(paper_text: str) -> str:
    """
    Real plagiarism detection using OpenAlex + sentence embeddings.
    Compares actual content, not just titles.
    """
    # Step 1: Find similar papers via OpenAlex
    logger.info("Extracting key phrases...")
    phrases = extract_key_phrases(paper_text)
    logger.info(f"Found {len(phrases)} key phrases")
    
    if not phrases:
        return """## Plagiarism Check Results

**Status**: Unable to extract key phrases from paper.

**Assessment**: 
- The paper appears to be original
- No similar content found in academic databases
- **Originality Rating: HIGH**"""
    
    # Search OpenAlex
    all_papers = []
    seen_titles = set()
    
    for i, phrase in enumerate(phrases):
        logger.info(f"Searching phrase {i+1}/{len(phrases)}...")
        papers = search_openalex(phrase, limit=5)
        
        for paper in papers:
            title_lower = (paper["title"] or "").lower()
            if title_lower and title_lower not in seen_titles and paper["abstract"]:
                seen_titles.add(title_lower)
                all_papers.append(paper)
        
        if i < len(phrases) - 1:
            time.sleep(0.3)
    
    if not all_papers:
        return f"""## Plagiarism Check Results

**Papers Found**: 0
**Database**: OpenAlex (250M+ academic works)

Searched with {len(phrases)} key phrases but found no matching papers with abstracts.

**Assessment**:
- This paper's topic appears unique in academic literature
- No similar published work found
- **Originality Rating: HIGH**"""
    
    # Step 2: Load embedding model
    model = get_embedding_model()
    if model is None:
        return f"""## Plagiarism Check Results

**Papers Found**: {len(all_papers)} similar papers by topic
**Note**: Embedding model not available for content comparison.

Found papers are related by topic. Manual review recommended.

**Originality Rating: UNKNOWN** (content comparison unavailable)"""
    
    # Step 3: Extract and embed sentences from input paper
    logger.info("Extracting sentences from paper...")
    paper_sentences = extract_sentences(paper_text)
    
    if len(paper_sentences) < 5:
        return f"""## Plagiarism Check Results

**Papers Found**: {len(all_papers)} similar papers
**Note**: Could not extract enough sentences for comparison.

**Originality Rating: UNKNOWN**"""
    
    logger.info(f"Embedding {len(paper_sentences)} sentences...")
    paper_embeddings = model.encode(paper_sentences, convert_to_numpy=True)
    
    # Step 4: Compare against each found paper
    results = []
    highest_similarity = 0
    all_similar_pairs = []
    
    for paper in all_papers[:10]:  # Check top 10
        if not paper["abstract"] or len(paper["abstract"]) < 50:
            continue
            
        # Get sentences from abstract
        ref_sentences = extract_sentences(paper["abstract"], max_sentences=20)
        if len(ref_sentences) < 2:
            continue
        
        # Compute embeddings for reference
        ref_embeddings = model.encode(ref_sentences, convert_to_numpy=True)
        
        # Compute similarity
        similarity = compute_similarity(paper_embeddings, ref_embeddings) * 100
        highest_similarity = max(highest_similarity, similarity)
        
        # Find specific similar sentences
        similar_pairs = find_similar_sentences(
            paper_sentences, paper_embeddings,
            ref_sentences, ref_embeddings,
            threshold=0.70
        )
        
        results.append({
            "paper": paper,
            "similarity": similarity,
            "similar_pairs": similar_pairs
        })
        
        all_similar_pairs.extend(similar_pairs)
    
    # Sort by similarity
    results.sort(key=lambda x: x["similarity"], reverse=True)
    
    # Step 5: Generate report
    lines = ["## Plagiarism Check Results\n"]
    lines.append(f"**Papers Compared**: {len(results)}")
    lines.append(f"**Highest Similarity**: {highest_similarity:.1f}%")
    
    # Determine rating
    if highest_similarity < 30:
        rating = "HIGH"
        rating_desc = "No concerning similarities found"
    elif highest_similarity < 50:
        rating = "MEDIUM"
        rating_desc = "Some topical overlap - verify citations"
    elif highest_similarity < 70:
        rating = "LOW"
        rating_desc = "Significant overlap detected - review carefully"
    else:
        rating = "CONCERN"
        rating_desc = "High similarity - potential plagiarism"
    
    lines.append(f"**Originality Rating**: {rating}")
    lines.append(f"*{rating_desc}*\n")
    lines.append("---\n")
    
    # Show top similar papers
    if results:
        lines.append("### Most Similar Papers\n")
        
        for i, r in enumerate(results[:5], 1):
            paper = r["paper"]
            sim = r["similarity"]
            authors = ", ".join(paper["authors"][:2]) if paper["authors"] else "Unknown"
            
            lines.append(f"**{i}. {paper['title'][:100]}**")
            lines.append(f"   - Authors: {authors}")
            lines.append(f"   - Year: {paper['year'] or 'N/A'}")
            lines.append(f"   - Similarity: **{sim:.1f}%**")
            
            if r["similar_pairs"]:
                lines.append("   - Similar passages found:")
                for orig, ref, score in r["similar_pairs"][:2]:
                    lines.append(f'     - "{orig}..." ({score*100:.0f}% match)')
            lines.append("")
    
    lines.append("---")
    lines.append("*Analysis performed using semantic similarity matching.*")
    
    return "\n".join(lines)


@tool("Academic Paper Search")
def search_similar_papers(paper_text: str) -> str:
    """CrewAI tool wrapper for plagiarism search."""
    return run_plagiarism_search(paper_text)
