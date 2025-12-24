"""
Enhanced Embedding Service
==========================

Core embedding service with additional utilities for:
- Text similarity computation
- Batch processing with chunking
- Embedding caching
- Cross-document similarity

This is the unified embedding service - all code should use this
instead of creating separate SentenceTransformer instances.
"""

from functools import lru_cache
from typing import List, Dict, Tuple, Optional, Union
import numpy as np
import torch
import logging

from sentence_transformers import SentenceTransformer, util

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Cache for document embeddings to avoid recomputation
_embedding_cache: Dict[str, np.ndarray] = {}


@lru_cache
def get_embedding_model() -> SentenceTransformer:
    """
    Get the cached embedding model.
    
    Uses the model specified in settings.EMBEDDING_MODEL_NAME.
    Model is loaded once and reused across all calls.
    """
    logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL_NAME}")
    model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
    
    # Use GPU if available
    if torch.cuda.is_available():
        model = model.to('cuda')
        logger.info("Embedding model loaded on GPU")
    else:
        logger.info("Embedding model loaded on CPU")
    
    return model


def embed_texts(
    texts: List[str],
    normalize: bool = True,
    batch_size: int = 32
) -> List[list]:
    """
    Embed a list of texts using the embedding model.
    
    Args:
        texts: List of texts to embed
        normalize: Whether to L2 normalize embeddings (recommended for cosine similarity)
        batch_size: Batch size for encoding
        
    Returns:
        List of embeddings as Python lists
    """
    if not texts:
        return []
        
    model = get_embedding_model()
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=normalize
    )
    return [v.tolist() for v in vectors]


def embed_texts_numpy(
    texts: List[str],
    normalize: bool = True,
    batch_size: int = 32
) -> np.ndarray:
    """
    Embed texts and return as numpy array for efficient computation.
    
    Args:
        texts: List of texts to embed
        normalize: Whether to L2 normalize embeddings
        batch_size: Batch size for encoding
        
    Returns:
        Numpy array of shape (num_texts, embedding_dim)
    """
    if not texts:
        return np.array([])
        
    model = get_embedding_model()
    return model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=normalize
    )


def compute_similarity(
    text1: str,
    text2: str
) -> float:
    """
    Compute cosine similarity between two texts.
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        Similarity score between 0 and 1
    """
    embeddings = embed_texts_numpy([text1, text2], normalize=True)
    if len(embeddings) < 2:
        return 0.0
    return float(np.dot(embeddings[0], embeddings[1]))


def compute_similarity_matrix(
    texts1: List[str],
    texts2: List[str]
) -> np.ndarray:
    """
    Compute pairwise similarity matrix between two lists of texts.
    
    Args:
        texts1: First list of texts
        texts2: Second list of texts
        
    Returns:
        Similarity matrix of shape (len(texts1), len(texts2))
    """
    if not texts1 or not texts2:
        return np.array([])
        
    emb1 = embed_texts_numpy(texts1, normalize=True)
    emb2 = embed_texts_numpy(texts2, normalize=True)
    
    return np.dot(emb1, emb2.T)


def find_most_similar(
    query: str,
    candidates: List[str],
    top_k: int = 5,
    threshold: float = 0.0
) -> List[Tuple[int, str, float]]:
    """
    Find the most similar candidates to a query.
    
    Args:
        query: Query text
        candidates: List of candidate texts to search
        top_k: Number of top results to return
        threshold: Minimum similarity threshold
        
    Returns:
        List of (index, text, score) tuples sorted by similarity
    """
    if not candidates:
        return []
        
    query_emb = embed_texts_numpy([query], normalize=True)[0]
    candidate_embs = embed_texts_numpy(candidates, normalize=True)
    
    # Compute similarities
    similarities = np.dot(candidate_embs, query_emb)
    
    # Get top-k indices
    results = []
    for i, score in enumerate(similarities):
        if score >= threshold:
            results.append((i, candidates[i], float(score)))
    
    # Sort by score descending
    results.sort(key=lambda x: x[2], reverse=True)
    return results[:top_k]


def semantic_chunk_similarity(
    chunk1: str,
    chunk2: str,
    sentence_level: bool = False
) -> Dict[str, float]:
    """
    Compute detailed similarity between two text chunks.
    
    Args:
        chunk1: First text chunk
        chunk2: Second text chunk
        sentence_level: Whether to also compute sentence-level similarities
        
    Returns:
        Dictionary with similarity metrics
    """
    # Overall similarity
    overall = compute_similarity(chunk1, chunk2)
    
    result = {
        'overall_similarity': overall,
        'is_highly_similar': overall > 0.8,
        'is_similar': overall > 0.6,
    }
    
    if sentence_level:
        # Split into sentences
        import re
        sentences1 = [s.strip() for s in re.split(r'[.!?]+', chunk1) if s.strip()]
        sentences2 = [s.strip() for s in re.split(r'[.!?]+', chunk2) if s.strip()]
        
        if sentences1 and sentences2:
            sim_matrix = compute_similarity_matrix(sentences1, sentences2)
            
            # Max similarity for each sentence in chunk1
            max_sims = np.max(sim_matrix, axis=1) if sim_matrix.size > 0 else []
            
            result['max_sentence_similarity'] = float(np.max(max_sims)) if len(max_sims) > 0 else 0.0
            result['avg_sentence_similarity'] = float(np.mean(max_sims)) if len(max_sims) > 0 else 0.0
            result['num_highly_similar_sentences'] = int(np.sum(np.array(max_sims) > 0.8))
    
    return result


def get_cached_embedding(
    text: str,
    cache_key: Optional[str] = None
) -> np.ndarray:
    """
    Get embedding from cache or compute and cache it.
    
    Args:
        text: Text to embed
        cache_key: Optional cache key (defaults to text hash)
        
    Returns:
        Embedding as numpy array
    """
    if cache_key is None:
        cache_key = str(hash(text))
    
    if cache_key not in _embedding_cache:
        embedding = embed_texts_numpy([text], normalize=True)[0]
        _embedding_cache[cache_key] = embedding
    
    return _embedding_cache[cache_key]


def clear_embedding_cache() -> None:
    """Clear the embedding cache."""
    global _embedding_cache
    _embedding_cache = {}
    logger.info("Embedding cache cleared")


def get_cache_stats() -> Dict[str, int]:
    """Get embedding cache statistics."""
    return {
        'cached_embeddings': len(_embedding_cache),
        'cache_size_mb': sum(e.nbytes for e in _embedding_cache.values()) / (1024 * 1024)
    }
