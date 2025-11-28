import os
import json
import pickle
import numpy as np
import faiss
from typing import List, Dict, Any, Optional
from app.config import get_settings
from app.utils.logging import logger

settings = get_settings()

class FaissService:
    def __init__(self):
        self.index_dir = settings.FAISS_INDEX_PATH
        self.index_file = os.path.join(self.index_dir, "index.faiss")
        self.metadata_file = os.path.join(self.index_dir, "metadata.pkl")
        
        self.dimension = settings.EMBEDDING_DIM
        self.index = None
        self.metadata_map = {}  # Map int ID -> Metadata Dict
        
        self._load_or_create_index()

    def _load_or_create_index(self):
        """Loads existing FAISS index or creates a new one."""
        os.makedirs(self.index_dir, exist_ok=True)
        
        if os.path.exists(self.index_file) and os.path.exists(self.metadata_file):
            try:
                self.index = faiss.read_index(self.index_file)
                with open(self.metadata_file, "rb") as f:
                    self.metadata_map = pickle.load(f)
                logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors.")
            except Exception as e:
                logger.error(f"Failed to load FAISS index: {e}. Creating new one.")
                self._create_new_index()
        else:
            self._create_new_index()

    def _create_new_index(self):
        """Creates a new IndexFlatIP (Inner Product) for cosine similarity."""
        # Note: Input vectors must be normalized for Inner Product to equal Cosine Similarity
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata_map = {}
        logger.info("Created new empty FAISS index.")

    def _save_index(self):
        """Persists the index and metadata to disk."""
        try:
            faiss.write_index(self.index, self.index_file)
            with open(self.metadata_file, "wb") as f:
                pickle.dump(self.metadata_map, f)
            logger.info("Saved FAISS index to disk.")
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {e}")

    def add_vectors(self, vectors: List[Dict[str, Any]]):
        """
        Add vectors to the index.
        vectors format: [{'values': [float], 'metadata': dict}, ...]
        """
        if not vectors:
            return

        try:
            # Prepare data
            embeddings = np.array([v['values'] for v in vectors]).astype('float32')
            
            # Normalize for Cosine Similarity (IndexFlatIP)
            faiss.normalize_L2(embeddings)
            
            # Current count is the starting ID for new vectors
            start_id = self.index.ntotal
            
            # Add to FAISS
            self.index.add(embeddings)
            
            # Add to metadata map
            for i, vec_data in enumerate(vectors):
                internal_id = start_id + i
                self.metadata_map[internal_id] = vec_data.get('metadata', {})
            
            # Save immediately (simple persistence strategy)
            self._save_index()
            
            logger.info(f"Added {len(vectors)} vectors to FAISS.")
            
        except Exception as e:
            logger.error(f"Failed to add vectors to FAISS: {e}")

    def search(self, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search the index. Returns list of matches with metadata and score.
        """
        if not self.index or self.index.ntotal == 0:
            return []

        try:
            # Prepare query
            xq = np.array([query_vector]).astype('float32')
            faiss.normalize_L2(xq)
            
            # Search
            distances, indices = self.index.search(xq, top_k)
            
            results = []
            for j, idx in enumerate(indices[0]):
                if idx == -1: continue # No result found
                
                score = float(distances[0][j])
                meta = self.metadata_map.get(idx, {})
                
                results.append({
                    "id": str(idx),
                    "score": score,
                    "metadata": meta
                })
                
            return results
            
        except Exception as e:
            logger.error(f"FAISS search failed: {e}")
            return []

# Singleton
faiss_service = FaissService()