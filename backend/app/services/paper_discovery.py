"""
paper_discovery.py - Embedding-based paper discovery for finding related arXiv papers.

Uses sentence embeddings and semantic similarity (inspired by get_papers.py) instead of web scraping.
Pure Python implementation with no external scraping dependencies.
"""

import logging
from typing import List, Dict, Any, Optional

try:
    import arxiv
    ARXIV_AVAILABLE = True
except ImportError:
    ARXIV_AVAILABLE = False
    arxiv = None

try:
    from sentence_transformers import SentenceTransformer, util
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    SentenceTransformer = None
    util = None

logger = logging.getLogger("research-analyzer")


class PaperDiscovery:
    """Discover related research papers using embedding-based similarity search."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize with a sentence embedding model.
        
        Args:
            model_name: Name of sentence-transformers model to use.
                       Default: all-MiniLM-L6-v2 (fast, lightweight)
        """
        if not EMBEDDINGS_AVAILABLE:
            logger.warning("sentence-transformers not installed; paper discovery unavailable")
            self.model = None
            return
        
        try:
            logger.debug(f"Loading embedding model: {model_name}")
            self.model = SentenceTransformer(model_name)
            logger.info(f"Loaded embedding model: {model_name}")
        except Exception as e:
            logger.warning(f"Failed to load embedding model: {e}")
            self.model = None
    
    def _is_available(self) -> bool:
        """Check if paper discovery is available."""
        return self.model is not None and EMBEDDINGS_AVAILABLE and ARXIV_AVAILABLE
    
    def embed_text(self, text: str):
        """Embed a text using the model."""
        if not self._is_available():
            return None
        
        try:
            embedding = self.model.encode(text, convert_to_tensor=True)
            return embedding
        except Exception as e:
            logger.debug(f"Failed to embed text: {e}")
            return None
    
    def embed_texts(self, texts: List[str]):
        """Embed multiple texts efficiently."""
        if not self._is_available():
            return None
        
        try:
            embeddings = self.model.encode(texts, convert_to_tensor=True)
            return embeddings
        except Exception as e:
            logger.debug(f"Failed to embed texts: {e}")
            return None
    
    def compute_similarity(self, query_embedding, candidate_embeddings):
        """Compute cosine similarity between query and candidates."""
        if not EMBEDDINGS_AVAILABLE or query_embedding is None or candidate_embeddings is None:
            return None
        
        try:
            scores = util.cos_sim(query_embedding, candidate_embeddings)[0]
            return scores
        except Exception as e:
            logger.debug(f"Failed to compute similarity: {e}")
            return None
    
    def fetch_paper_by_id(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Fetch paper metadata from arXiv by ID.
        
        Args:
            paper_id: arXiv paper ID (e.g., "2101.12345")
        
        Returns:
            Paper dict with title, abstract, authors, etc., or None if not found
        """
        if not ARXIV_AVAILABLE:
            return None
        
        try:
            search = arxiv.Search(id_list=[paper_id])
            paper = next(search.results(), None)
            
            if not paper:
                return None
            
            return {
                "arxiv_id": paper_id,
                "entry_id": paper.entry_id,
                "title": paper.title,
                "abstract": paper.summary,
                "summary": paper.summary,  # Also provide as 'summary' for compatibility
                "authors": [a.name for a in paper.authors] if paper.authors else [],
                "published": paper.published,
                "categories": paper.categories,
                "pdf_url": paper.pdf_url,
                "url": paper.pdf_url or paper.entry_id,  # Provide as 'url' for parquet store
            }
        except Exception as e:
            logger.debug(f"Failed to fetch paper {paper_id}: {e}")
            return None
    
    def search_arxiv_by_category(
        self,
        category: str,
        query: Optional[str] = None,
        max_results: int = 200,
    ) -> List[Dict[str, Any]]:
        """Search arXiv by category with optional keyword query.
        
        Common categories:
        - cs.CL: Computation and Language (NLP)
        - cs.CV: Computer Vision
        - cs.AI: Artificial Intelligence
        - cs.LG: Machine Learning
        - math.CA: Classical Analysis and ODEs
        
        Args:
            category: arXiv category (e.g., "cs.CL")
            query: Optional keyword query
            max_results: Max number of results to fetch
        
        Returns:
            List of paper dicts
        """
        if not ARXIV_AVAILABLE:
            return []
        
        try:
            # Build query
            if query:
                search_query = f"cat:{category} AND {query}"
            else:
                search_query = f"cat:{category}"
            
            logger.debug(f"Searching arXiv: {search_query} (max {max_results} results)")
            
            search = arxiv.Search(query=search_query, max_results=max_results)
            papers = []
            
            for result in search.results():
                papers.append({
                    "arxiv_id": result.get_short_id(),
                    "entry_id": result.entry_id,
                    "title": result.title,
                    "abstract": result.summary,
                    "summary": result.summary,  # Also provide as 'summary' for compatibility
                    "authors": [a.name for a in result.authors] if result.authors else [],
                    "published": result.published,
                    "categories": result.categories,
                    "pdf_url": result.pdf_url,
                    "url": result.pdf_url or result.entry_id,  # Provide as 'url' for parquet store
                })
            
            logger.info(f"Found {len(papers)} papers in {category}")
            return papers
        except Exception as e:
            logger.warning(f"Failed to search arXiv: {e}")
            return []
    
    def find_related_papers(
        self,
        target_paper: Dict[str, Any],
        category: str = "cs.CL",
        top_k: int = 10,
        max_candidates: int = 200,
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Find papers related to a target paper using embedding-based similarity.
        
        Pipeline (inspired by get_papers.py):
        1. Embed target paper abstract
        2. Search arXiv for candidate papers in category
        3. Embed all candidate abstracts
        4. Compute similarity scores
        5. Return top-k most similar papers
        
        Args:
            target_paper: Dict with 'abstract' or 'summary' key
            category: arXiv category to search within
            top_k: Number of related papers to return
            max_candidates: Max candidates to search (higher = slower but more thorough)
            query: Optional keyword query to filter candidates
        
        Returns:
            List of related paper dicts with similarity scores, sorted by similarity descending
        """
        if not self._is_available():
            logger.warning("Paper discovery not available")
            return []
        
        # Get target abstract
        target_abstract = target_paper.get("abstract") or target_paper.get("summary")
        if not target_abstract:
            logger.warning("Target paper has no abstract")
            return []
        
        # Embed target
        logger.debug("Embedding target paper abstract...")
        target_embedding = self.embed_text(target_abstract)
        if target_embedding is None:
            logger.warning("Failed to embed target paper")
            return []
        
        # Search for candidates
        logger.info(f"Searching {category} for up to {max_candidates} candidates...")
        candidates = self.search_arxiv_by_category(
            category=category,
            query=query,
            max_results=max_candidates
        )
        
        if not candidates:
            logger.warning(f"No candidates found in {category}")
            return []
        
        # Extract target ID to exclude it
        target_id = target_paper.get("arxiv_id") or target_paper.get("entry_id")
        candidates = [c for c in candidates if c.get("arxiv_id") != target_id]
        
        if not candidates:
            logger.warning("No candidates after filtering")
            return []
        
        # Embed candidates
        logger.debug(f"Embedding {len(candidates)} candidate abstracts...")
        candidate_abstracts = [c.get("abstract", "") for c in candidates]
        candidate_embeddings = self.embed_texts(candidate_abstracts)
        
        if candidate_embeddings is None:
            logger.warning("Failed to embed candidates")
            return []
        
        # Compute similarity
        logger.debug("Computing similarity scores...")
        scores = self.compute_similarity(target_embedding, candidate_embeddings)
        
        if scores is None:
            logger.warning("Failed to compute similarity")
            return []
        
        # Get top-k
        try:
            top_results = scores.topk(min(top_k, len(candidates)))
        except Exception as e:
            logger.warning(f"Failed to get top-k results: {e}")
            return []
        
        # Build result list with scores
        related_papers = []
        for score, idx in zip(top_results.values, top_results.indices):
            paper = candidates[int(idx)].copy()
            paper["similarity_score"] = float(score)
            related_papers.append(paper)
        
        logger.info(f"Found {len(related_papers)} related papers")
        return related_papers
    
    def find_related_papers_by_id(
        self,
        paper_id: str,
        category: str = "cs.CL",
        top_k: int = 10,
        max_candidates: int = 200,
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Find papers related to a paper specified by arXiv ID.
        
        Args:
            paper_id: arXiv paper ID
            category: Category to search within
            top_k: Number of results
            max_candidates: Max candidates to search
            query: Optional keyword query
        
        Returns:
            List of related papers with similarity scores
        """
        # Fetch target paper
        logger.debug(f"Fetching target paper {paper_id}...")
        target_paper = self.fetch_paper_by_id(paper_id)
        
        if not target_paper:
            logger.warning(f"Could not fetch paper {paper_id}")
            return []
        
        # Find related
        return self.find_related_papers(
            target_paper=target_paper,
            category=category,
            top_k=top_k,
            max_candidates=max_candidates,
            query=query,
        )


# Global instance
_discovery = None


def get_discovery() -> Optional[PaperDiscovery]:
    """Get or create the global paper discovery instance."""
    global _discovery
    if _discovery is None:
        _discovery = PaperDiscovery()
    return _discovery


def find_related_papers_to_abstract(
    abstract: str,
    category: str = "cs.CL",
    top_k: int = 10,
    max_candidates: int = 200,
) -> List[Dict[str, Any]]:
    """Convenience function to find related papers by abstract text.
    
    Args:
        abstract: Paper abstract or summary text
        category: arXiv category to search
        top_k: Number of papers to return
        max_candidates: Max candidates to search
    
    Returns:
        List of related papers with similarity scores
    """
    discovery = get_discovery()
    if not discovery:
        return []
    
    return discovery.find_related_papers(
        target_paper={"abstract": abstract},
        category=category,
        top_k=top_k,
        max_candidates=max_candidates,
    )
