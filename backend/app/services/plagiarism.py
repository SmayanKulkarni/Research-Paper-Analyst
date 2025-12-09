from typing import List, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder
from pinecone_text.sparse import BM25Encoder

from app.config import get_settings
from app.services.pinecone_client import pinecone_service
from app.utils.logging import logger

settings = get_settings()

class PlagiarismEngine:
    def __init__(self):
        logger.info("Initializing Plagiarism Engine (Hybrid + Cross-Encoder)...")
        # Heavy models are loaded lazily to speed up import times.
        self._dense_model = None
        self._cross_encoder = None
        self._bm25 = None

    @property
    def dense_model(self):
        if self._dense_model is None:
            self._dense_model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        return self._dense_model

    @property
    def cross_encoder(self):
        if self._cross_encoder is None:
            self._cross_encoder = CrossEncoder(settings.CROSS_ENCODER_MODEL)
        return self._cross_encoder

    @property
    def bm25(self):
        if self._bm25 is None:
            self._bm25 = BM25Encoder.default()
        return self._bm25

    def _sliding_window(self, text: str, chunk_size: int = 250, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks of words."""
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i : i + chunk_size])
            if len(chunk) > 50: # Ignore tiny chunks
                chunks.append(chunk)
        return chunks

    def check_document(self, text: str) -> List[Dict[str, Any]]:
        """
        Run deep plagiarism check on the document.
        """
        # Chunking handles ANY length of text
        chunks = self._sliding_window(
            text, 
            chunk_size=settings.PLAGIARISM_CHUNK_SIZE, 
            overlap=settings.PLAGIARISM_CHUNK_OVERLAP
        )
        logger.info(f"Checking {len(chunks)} chunks for plagiarism...")

        suspicious_matches = []

        for i, chunk in enumerate(chunks):
            # Generate Vectors
            dense_vec = self.dense_model.encode(chunk).tolist()
            sparse_vec = self.bm25.encode_queries(chunk)

            # Hybrid Search
            matches = pinecone_service.query_hybrid(
                dense_vector=dense_vec,
                sparse_vector=sparse_vec,
                top_k=5
            )

            if not matches: continue

            # Cross-Encoder Re-ranking
            pairs = []
            valid_matches = []
            
            for m in matches:
                retrieved_text = m.metadata.get("text", "")
                if retrieved_text:
                    pairs.append([chunk, retrieved_text])
                    valid_matches.append(m)

            if not pairs: continue

            scores = self.cross_encoder.predict(pairs)

            for idx, score in enumerate(scores):
                if score > 0.75:
                    match_meta = valid_matches[idx].metadata
                    suspicious_matches.append({
                        "chunk_index": i,
                        "suspicious_segment": chunk[:200] + "...",
                        "source_title": match_meta.get("title", "Unknown"),
                        "source_url": match_meta.get("url", ""),
                        "similarity_score": float(score),
                        "detection_method": "Hybrid+CrossEncoder"
                    })

        # Deduplicate
        unique_sources = {}
        for m in suspicious_matches:
            url = m["source_url"]
            if url not in unique_sources or m["similarity_score"] > unique_sources[url]["similarity_score"]:
                unique_sources[url] = m

        return list(unique_sources.values())

_plagiarism_engine: PlagiarismEngine | None = None


def _get_engine() -> PlagiarismEngine:
    global _plagiarism_engine
    if _plagiarism_engine is None:
        _plagiarism_engine = PlagiarismEngine()
    return _plagiarism_engine


def check_plagiarism(text: str) -> List[Dict[str, Any]]:
    return _get_engine().check_document(text)