import os
import re
import arxiv
import PyPDF2
from typing import List, Optional, Dict, Any
from sentence_transformers import SentenceTransformer, util
# Removed pinecone-text import as we are moving to standard FAISS dense search
# from pinecone_text.sparse import BM25Encoder 

from app.config import get_settings
from app.utils.logging import logger
from app.services.parquet_store import append_new_papers
# CHANGED: Import FAISS service instead of Pinecone
from app.services.faiss_client import faiss_service

settings = get_settings()

class PaperDiscoveryService:
    def __init__(self):
        self.download_dir = os.path.join(settings.STORAGE_ROOT, "downloads")
        os.makedirs(self.download_dir, exist_ok=True)
        
        # Initialize Models
        logger.info("Loading Embedding models for Discovery...")
        self.dense_model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        
        # Removed BM25 init as we are focusing on Dense FAISS search

    def find_arxiv_id_in_pdf(self, pdf_path: str) -> Optional[str]:
        if not os.path.exists(pdf_path): return None
        try:
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                # Read first 3 pages to find ID
                text = "".join([page.extract_text() or "" for page in reader.pages[:3]])
            match = re.search(r'(?:arXiv:)?(\d{4}\.\d{4,5})(?:v\d+)?', text)
            return match.group(1) if match else None
        except Exception:
            return None

    def find_similar_papers(self, source_pdf_path: str, category: str = "cat:cs.CL") -> List[Dict[str, Any]]:
        # 1. Extract ID
        paper_id = self.find_arxiv_id_in_pdf(source_pdf_path)
        if not paper_id:
            logger.warning("No ArXiv ID found. Skipping discovery.")
            return []

        # 2. Get Source Abstract
        try:
            target_paper = next(arxiv.Search(id_list=[paper_id]).results(), None)
            if not target_paper: return []
            target_abstract = target_paper.summary
        except: return []

        # 3. Dense Encode Target
        target_emb = self.dense_model.encode(target_abstract, convert_to_tensor=True)

        # 4. Search Candidates
        logger.info("Searching ArXiv for candidates...")
        results = list(arxiv.Search(query=category, max_results=50).results())
        
        candidates = [r for r in results if paper_id not in r.entry_id]
        if not candidates: return []
        
        cand_abstracts = [r.summary for r in candidates]
        
        # 5. Compute Similarity
        cand_embs = self.dense_model.encode(cand_abstracts, convert_to_tensor=True)
        scores = util.cos_sim(target_emb, cand_embs)[0]
        
        # 6. Process Top 10
        top_k_indices = scores.topk(min(20, len(candidates))).indices
        
        new_papers = []
        vectors_to_index = []

        for idx in top_k_indices:
            p = candidates[idx]
            abstract = cand_abstracts[idx]
            
            # Prepare Data
            dense_vec = cand_embs[idx].tolist()
            
            # Record for Parquet/Local
            # Note: We keep the structure mostly the same, but sparse_values will be None
            new_papers.append({
                "title": p.title,
                "summary": abstract,
                "url": p.entry_id,
                "embedding": dense_vec,
                "sparse_values": None 
            })
            
            # Record for FAISS (Vector DB)
            vectors_to_index.append({
                "values": dense_vec,
                "metadata": {
                    "title": p.title,
                    "text": abstract,
                    "url": p.entry_id
                }
            })

        # 7. Save to Parquet
        saved = append_new_papers(new_papers)
        
        # 8. Add to FAISS
        if vectors_to_index:
            logger.info("Indexing papers to FAISS for Plagiarism checks...")
            faiss_service.add_vectors(vectors_to_index)

        return saved