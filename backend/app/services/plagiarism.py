from typing import List, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer

# Removed CrossEncoder import
from app.config import get_settings
from app.services.faiss_client import faiss_service
from app.utils.logging import logger

settings = get_settings()

class PlagiarismEngine:
    def __init__(self):
        logger.info("Initializing Plagiarism Engine (FAISS Dense Only)...")
        self.dense_model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        # Removed CrossEncoder initialization

    def _sliding_window(self, text: str, chunk_size: int = 250, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks of words."""
        words = text.split()
        chunks = []
        step = chunk_size - overlap
        if step < 1: step = 1
            
        for i in range(0, len(words), step):
            chunk = " ".join(words[i : i + chunk_size])
            if len(chunk) > 50:
                chunks.append(chunk)
        return chunks

    def check_document(self, text: str) -> List[Dict[str, Any]]:
        """
        Run plagiarism check using simple Vector Similarity (FAISS).
        """
        if not faiss_service.index:
            logger.error("FAISS index unavailable. Skipping plagiarism check.")
            return [{"error": "Plagiarism service unavailable."}]

        chunks = self._sliding_window(
            text, 
            chunk_size=settings.PLAGIARISM_CHUNK_SIZE, 
            overlap=settings.PLAGIARISM_CHUNK_OVERLAP
        )
        logger.info(f"Checking {len(chunks)} chunks for plagiarism...")

        suspicious_matches = []

        for i, chunk in enumerate(chunks):
            try:
                # Generate Dense Vector
                dense_vec = self.dense_model.encode(chunk).tolist()
                
                # Search FAISS
                matches = faiss_service.search(
                    query_vector=dense_vec,
                    top_k=3 # Reduced to top 3 since we don't re-rank
                )

                if not matches:
                    continue

                for m in matches:
                    # Retrieve metadata
                    score = m.get('score', 0)
                    match_meta = m.get('metadata', {})
                    
                    # Threshold check (Cosine Similarity usually needs > 0.8 to be meaningful plagiarism)
                    if score > 0.80:
                        suspicious_matches.append({
                            "chunk_index": i,
                            "suspicious_segment": chunk[:200] + "...", 
                            "source_title": match_meta.get("title", "Unknown"),
                            "source_url": match_meta.get("url", ""),
                            "similarity_score": float(score),
                            "detection_method": "FAISS-Only"
                        })

            except Exception as e:
                logger.warning(f"Error checking chunk {i}: {e}")
                continue

        unique_sources = {}
        for m in suspicious_matches:
            url = m["source_url"]
            if url not in unique_sources or m["similarity_score"] > unique_sources[url]["similarity_score"]:
                unique_sources[url] = m

        return list(unique_sources.values())

plagiarism_engine = PlagiarismEngine()

def check_plagiarism(text: str) -> List[Dict[str, Any]]:
    return plagiarism_engine.check_document(text)