import os
import re
import arxiv
import PyPDF2
from typing import List, Optional, Dict, Any
from sentence_transformers import SentenceTransformer, util

from app.config import get_settings
from app.utils.logging import logger
from app.services.parquet_store import append_new_papers

settings = get_settings()

class PaperDiscoveryService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the service with the embedding model.
        """
        self.download_dir = os.path.join(settings.STORAGE_ROOT, "downloads")
        os.makedirs(self.download_dir, exist_ok=True)
        
        logger.info(f"Loading SentenceTransformer model: {model_name}")
        self.model = SentenceTransformer(model_name)

    def find_arxiv_id_in_pdf(self, pdf_path: str) -> Optional[str]:
        """
        Extracts arXiv ID from the first few pages of a PDF file using Regex.
        """
        if not os.path.exists(pdf_path):
            logger.error(f"PDF not found at {pdf_path}")
            return None

        try:
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                # Check first 3 pages usually enough for header
                for i in range(min(len(reader.pages), 3)): 
                    text += reader.pages[i].extract_text() or ""

            # Regex to find standard ArXiv IDs (e.g., 1906.00579 or arXiv:1906.00579)
            pattern = r'(?:arXiv:)?(\d{4}\.\d{4,5})(?:v\d+)?'
            match = re.search(pattern, text)
            
            if match:
                logger.info(f"Found ArXiv ID: {match.group(1)}")
                return match.group(1)
            else:
                logger.warning("No ArXiv ID found in PDF text.")
                return None
                
        except Exception as e:
            logger.error(f"Failed to extract ID from PDF: {e}")
            return None

    def find_similar_papers(
        self, 
        source_pdf_path: str, 
        category: str = "cat:cs.CL", 
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Main pipeline:
        1. Extract ID from local PDF
        2. Fetch abstract from ArXiv
        3. Search for candidates in category
        4. Calculate similarity
        5. Download top matches
        6. Save metadata to Parquet
        """
        
        # 1. Get ID from PDF
        paper_id = self.find_arxiv_id_in_pdf(source_pdf_path)
        if not paper_id:
            logger.error("Cannot proceed without a valid ArXiv ID.")
            return []

        # 2. Get target abstract
        try:
            search = arxiv.Search(id_list=[paper_id])
            target_paper = next(search.results(), None)
            
            if not target_paper:
                logger.error(f"Paper {paper_id} not found on ArXiv.")
                return []
                
            target_abstract = target_paper.summary
            logger.info(f"Target Paper: {target_paper.title}")
            
        except Exception as e:
            logger.error(f"Error fetching target paper details: {e}")
            return []

        # 3. Encode target
        target_emb = self.model.encode(target_abstract, convert_to_tensor=True)

        # 4. Search for candidates
        logger.info(f"Searching ArXiv for candidates in {category}...")
        search_results = arxiv.Search(query=category, max_results=200)

        candidate_papers = []
        candidate_abstracts = []

        for r in search_results.results():
            # Skip the paper itself
            if paper_id in r.entry_id:
                continue
            candidate_papers.append(r)
            candidate_abstracts.append(r.summary)

        if not candidate_papers:
            logger.warning("No candidate papers found.")
            return []

        # 5. Encode candidates
        logger.info(f"Encoding {len(candidate_abstracts)} candidate abstracts...")
        candidate_embs = self.model.encode(candidate_abstracts, convert_to_tensor=True)

        # 6. Compute similarities
        cos_scores = util.cos_sim(target_emb, candidate_embs)[0]
        top_results = cos_scores.topk(min(top_k, len(candidate_papers)))

        logger.info(f"Found {len(top_results.indices)} similar papers.")
        
        papers_to_save = []

        # 7. Process Top Results
        for score, idx in zip(top_results.values, top_results.indices):
            p = candidate_papers[idx]
            similarity_score = score.item()
            
            # Download PDF
            try:
                # Use safe filename
                safe_id = p.get_short_id()
                pdf_name = f"{safe_id}.pdf"
                
                # Check if already exists to save bandwidth
                final_path = os.path.join(self.download_dir, pdf_name)
                if not os.path.exists(final_path):
                    p.download_pdf(dirpath=self.download_dir, filename=pdf_name)
                    logger.info(f"Downloaded: {p.title}")
                else:
                    logger.info(f"Already exists: {p.title}")

                # Prepare for Parquet
                papers_to_save.append({
                    "title": p.title,
                    "summary": p.summary,
                    "url": p.entry_id,
                    "embedding": candidate_embs[idx].tolist(), # Convert Tensor to list for JSON/Parquet
                    "similarity": similarity_score # Extra metadata if needed later
                })
                
            except Exception as e:
                logger.error(f"Failed to process candidate {p.entry_id}: {e}")

        # 8. Save to Parquet
        if papers_to_save:
            saved_records = append_new_papers(papers_to_save)
            logger.info(f"Pipeline complete. Saved {len(saved_records)} new records to database.")
            return saved_records
        
        return []

# Helper function for quick usage
def run_paper_discovery(pdf_path: str):
    service = PaperDiscoveryService()
    return service.find_similar_papers(pdf_path)