from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
from app.config import get_settings
from app.utils.logging import logger

settings = get_settings()

class PineconeService:
    def __init__(self):
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index_name = settings.PINECONE_INDEX_NAME
        self._ensure_index_exists()
        self.index = self.pc.Index(self.index_name)

    def _ensure_index_exists(self):
        """Create index if it doesn't exist."""
        existing_indexes = self.pc.list_indexes().names()
        if self.index_name not in existing_indexes:
            logger.info(f"Creating Pinecone index: {self.index_name}")
            # Assuming Serverless (Starter) or Pod-based based on env. 
            # Defaulting to a generic config compatible with most plans.
            self.pc.create_index(
                name=self.index_name,
                dimension=settings.EMBEDDING_DIM,
                metric="dotproduct", # Optimized for hybrid search
                spec=ServerlessSpec(
                    cloud="aws",
                    region=settings.PINECONE_ENVIRONMENT
                )
            )

    def upsert_vectors(self, vectors: List[Dict[str, Any]]):
        """
        Batch upsert vectors.
        vectors format: [{'id': '...', 'values': [...], 'sparse_values': {...}, 'metadata': {...}}]
        """
        try:
            # Upsert in batches of 100 to avoid request size limits
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i : i + batch_size]
                self.index.upsert(vectors=batch)
            logger.info(f"Successfully upserted {len(vectors)} vectors to Pinecone.")
        except Exception as e:
            logger.error(f"Failed to upsert vectors: {e}")

    def query_hybrid(
        self, 
        dense_vector: List[float], 
        sparse_vector: Optional[Dict[str, Any]] = None, 
        top_k: int = 5,
        alpha: float = 0.5 # Weight between dense (0.0) and sparse (1.0)
    ) -> List[Any]:
        """
        Perform Hybrid Search (Dense + Sparse).
        """
        try:
            # Pinecone client handles the weighting internally if using dotproduct
            # Note: For explicit alpha weighting, you usually scale vectors client-side.
            # Here we pass both if available.
            
            results = self.index.query(
                vector=dense_vector,
                sparse_vector=sparse_vector,
                top_k=top_k,
                include_metadata=True
            )
            return results.matches
        except Exception as e:
            logger.error(f"Pinecone query failed: {e}")
            return []

# Singleton instance
pinecone_service = PineconeService()