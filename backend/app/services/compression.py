"""
compression.py - Non-LLM text compression using extractive summarization.

Compresses research paper chunks by:
1. Extracting key sentences (TF-IDF scoring)
2. Removing redundancy (deduplication)
3. Preserving structure (sections, lists, equations)
4. Maintaining flow (keeps transition words)

This is pure NLP with no LLM calls.
"""

import re
from typing import List
from app.utils.logging import logger


def _score_sentences_by_tfidf(text: str, top_k: int = 0.5) -> List[tuple]:
    """Score sentences by TF-IDF importance.
    
    Args:
        text: Input text with sentences
        top_k: Fraction (0-1) of sentences to keep, or absolute count if > 1
    
    Returns:
        List of (sentence, score) tuples sorted by score descending
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from nltk.tokenize import sent_tokenize
    except ImportError:
        logger.debug("sklearn/nltk not available; using simple sentence extraction")
        return _score_sentences_simple(text, top_k)
    
    try:
        # Tokenize into sentences
        sentences = sent_tokenize(text)
        if not sentences:
            return []
        
        # Build TF-IDF matrix
        vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(sentences)
        
        # Score each sentence by sum of TF-IDF scores
        scores = tfidf_matrix.sum(axis=1).A1
        
        # Sort by score
        scored = [(sentences[i], float(scores[i])) for i in range(len(sentences))]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return scored
    except Exception as e:
        logger.debug(f"TF-IDF scoring failed: {e}; using simple extraction")
        return _score_sentences_simple(text, top_k)


def _score_sentences_simple(text: str, top_k: float = 0.5) -> List[tuple]:
    """Simple sentence scoring without ML libraries.
    
    Scores based on:
    - Sentence length (avoid very short/long)
    - Presence of technical terms (numbers, keywords)
    - Position (first sentences in paragraphs)
    """
    # Split by periods, but preserve abbreviations
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return []
    
    scored = []
    for i, sent in enumerate(sentences):
        score = 0.0
        
        # Length preference: 10-100 words is ideal
        word_count = len(sent.split())
        if 10 <= word_count <= 100:
            score += 1.0
        elif 5 <= word_count <= 200:
            score += 0.5
        
        # Technical content: has numbers, percentages, equations
        if re.search(r'\d+\.\d+|\d+%|=|≈|≤|≥', sent):
            score += 1.5
        
        # Keywords: common research terms
        keywords = ['propose', 'demonstrate', 'show', 'result', 'method', 'novel', 'improve', 'achieve']
        if any(kw in sent.lower() for kw in keywords):
            score += 1.0
        
        # Position: first sentence in text or after section header
        if i < 3 or (i > 0 and re.match(r'^[A-Z\d\s:]+$', sentences[i-1])):
            score += 0.5
        
        scored.append((sent, score))
    
    return sorted(scored, key=lambda x: x[1], reverse=True)


def _select_top_sentences(scored_sentences: List[tuple], top_k: float = 0.5, original_text: str = "") -> List[str]:
    """Select top-scoring sentences while preserving original order.
    
    Args:
        scored_sentences: List of (sentence, score) tuples
        top_k: Fraction (0-1) or count of sentences to keep
        original_text: Original text to preserve order
    
    Returns:
        Selected sentences in original order
    """
    if not scored_sentences:
        return []
    
    # Determine how many sentences to keep
    if isinstance(top_k, float) and 0 < top_k < 1:
        keep_count = max(1, int(len(scored_sentences) * top_k))
    else:
        keep_count = max(1, int(top_k))
    
    # Get top sentences
    top_sentences = set(sent for sent, _ in scored_sentences[:keep_count])
    
    # Preserve original order
    selected = []
    for sent in scored_sentences:
        if sent[0] in top_sentences:
            selected.append(sent[0])
            top_sentences.discard(sent[0])
    
    # If original_text provided, preserve original order
    if original_text:
        # Split original and keep in order
        sentences_in_doc = re.split(r'(?<=[.!?])\s+(?=[A-Z])', original_text)
        sentences_in_doc = [s.strip() for s in sentences_in_doc if s.strip()]
        
        result = []
        for sent in sentences_in_doc:
            if sent in top_sentences:
                result.append(sent)
                top_sentences.discard(sent)
        return result
    
    return selected


def _remove_redundancy(sentences: List[str], similarity_threshold: float = 0.9) -> List[str]:
    """Remove nearly-duplicate or highly similar sentences.
    
    Uses simple word overlap as similarity measure.
    """
    if not sentences or len(sentences) <= 1:
        return sentences
    
    kept = []
    for sent in sentences:
        # Check against previously kept sentences
        is_duplicate = False
        sent_words = set(sent.lower().split())
        
        for kept_sent in kept:
            kept_words = set(kept_sent.lower().split())
            
            # Calculate Jaccard similarity
            if len(sent_words) > 0 and len(kept_words) > 0:
                intersection = len(sent_words & kept_words)
                union = len(sent_words | kept_words)
                similarity = intersection / union if union > 0 else 0
                
                if similarity >= similarity_threshold:
                    is_duplicate = True
                    break
        
        if not is_duplicate:
            kept.append(sent)
    
    return kept


def compress_text_chunk(
    chunk: str,
    compression_ratio: float = 0.5,
    preserve_structure: bool = True
) -> str:
    """Compress a text chunk using extractive summarization.
    
    Args:
        chunk: Text to compress
        compression_ratio: Target compression (0-1). 0.5 = keep 50% of sentences
        preserve_structure: Keep section headers, lists, code blocks
    
    Returns:
        Compressed text
    """
    if not chunk or len(chunk.strip()) < 50:
        return chunk
    
    # Preserve headers and structure
    lines = chunk.split('\n')
    structure_lines = []
    content_lines = []
    
    for line in lines:
        # Detect headers (### Header, # Header, etc.)
        if re.match(r'^#+\s', line):
            structure_lines.append(line)
            continue
        
        # Detect lists
        if re.match(r'^\s*[-*•]\s', line):
            structure_lines.append(line)
            continue
        
        # Detect equations or code blocks
        if re.match(r'^\s*```|^\s*\$\$', line):
            structure_lines.append(line)
            continue
        
        if line.strip():
            content_lines.append(line)
    
    # Compress content
    if content_lines:
        content_text = '\n'.join(content_lines)
        
        # Score sentences
        scored = _score_sentences_by_tfidf(content_text, top_k=compression_ratio)
        
        # Select top sentences in original order
        selected = _select_top_sentences(scored, top_k=compression_ratio, original_text=content_text)
        
        # Remove redundancy
        selected = _remove_redundancy(selected)
        
        # Reconstruct
        compressed_content = ' '.join(selected)
    else:
        compressed_content = ''
    
    # Interleave structure and content
    result = structure_lines
    if compressed_content:
        result.extend(compressed_content.split('\n'))
    
    return '\n'.join(result)


def compress_text_with_ratio(text: str, target_ratio: float = 0.5) -> str:
    """Compress text to approximately target ratio using extractive summarization.
    
    Args:
        text: Text to compress
        target_ratio: Target ratio (0.5 = 50% of original, 0.3 = 30%, etc.)
    
    Returns:
        Compressed text
    """
    if not text or len(text) < 100:
        return text
    
    original_len = len(text)
    
    # For very large texts, use aggressive compression
    if original_len > 5000:
        ratio = min(target_ratio, 0.4)
    else:
        ratio = target_ratio
    
    try:
        # Score sentences
        scored = _score_sentences_by_tfidf(text, top_k=ratio)
        
        if not scored:
            return text
        
        # Select sentences
        selected = _select_top_sentences(scored, top_k=ratio, original_text=text)
        
        if not selected:
            return text
        
        # Remove redundancy
        selected = _remove_redundancy(selected)
        
        # Reconstruct with spacing
        compressed = ' '.join(selected)
        
        # Log compression stats
        logger.debug(
            f"Compression: {original_len} chars → {len(compressed)} chars "
            f"({100*len(compressed)/original_len:.1f}%)"
        )
        
        return compressed
    except Exception as e:
        logger.debug(f"Compression failed: {e}; returning original text")
        return text


def batch_compress_chunks(
    chunks: List[str],
    compression_ratio: float = 0.5
) -> List[str]:
    """Compress multiple text chunks.
    
    Args:
        chunks: List of text chunks
        compression_ratio: Target compression ratio (0-1)
    
    Returns:
        List of compressed chunks
    """
    compressed = []
    for chunk in chunks:
        try:
            comp = compress_text_with_ratio(chunk, target_ratio=compression_ratio)
            compressed.append(comp)
        except Exception as e:
            logger.debug(f"Failed to compress chunk: {e}; using original")
            compressed.append(chunk)
    
    return compressed
