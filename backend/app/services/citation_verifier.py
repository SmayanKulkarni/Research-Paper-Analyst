import re
from typing import List, Dict, Optional, Any
from semanticscholar import SemanticScholar
from app.config import get_settings
from app.utils.logging import logger

settings = get_settings()

class CitationVerifierService:
    def __init__(self):
        # Initialize Semantic Scholar Client (No API key needed for low volume, but better with one)
        self.sch = SemanticScholar(timeout=10)

    def extract_claims_with_citations(self, text: str) -> List[Dict[str, str]]:
        """
        Extract sentences that contain citations like [1], [12], (Author, 2020).
        This uses Regex to find the pattern and captures the surrounding sentence.
        """
        # Pattern for [1], [1, 2], [1-3]
        numeric_pattern = r'(\.?[^\.]*?\[\d+(?:[–,-]\d+)*\][^\.]*\.)'
        
        matches = re.findall(numeric_pattern, text)
        claims = []
        
        for match in matches:
            # Clean up the sentence
            clean_claim = match.strip()
            # Extract the specific ID inside
            ref_ids = re.findall(r'\[(\d+)\]', clean_claim)
            
            if ref_ids:
                claims.append({
                    "claim_text": clean_claim,
                    "ref_id": ref_ids[0] # Focus on the first citation found in sentence
                })
        
        return claims

    def resolve_reference_title(self, text: str, ref_id: str) -> Optional[str]:
        """
        Attempts to find the References section and look up what "[1]" actually is.
        """
        # Heuristic: Find section starting with "References"
        ref_section_match = re.search(r'(?i)references\s*\n', text)
        if not ref_section_match:
            return None
            
        ref_text = text[ref_section_match.end():]
        
        # Look for the specific line starting with [1]
        # Matches: [1] A. Author, "Title", Journal...
        pattern = re.escape(f"[{ref_id}]") + r'\s*(.*?)(?=\n\[\d+\]|\Z)'
        match = re.search(pattern, ref_text, re.DOTALL)
        
        if match:
            # Clean newlines from the title/citation string
            return match.group(1).replace('\n', ' ').strip()
        return None

    def verify_claim(self, claim: str, ref_title_blob: str) -> Dict[str, Any]:
        """
        1. Search Semantic Scholar for the paper title.
        2. Get the Abstract.
        3. (Logic usually handled by Agent, but we prep data here).
        """
        try:
            # 1. Search S2
            # We assume the blob contains the title. We take the first 10 words as search query usually works best
            search_query = " ".join(ref_title_blob.split()[:15]) 
            results = self.sch.search_paper(search_query, limit=1)
            
            if not results:
                return {"status": "not_found", "reason": "Paper not found on Semantic Scholar"}
            
            paper = results[0]
            abstract = paper.abstract
            
            if not abstract:
                return {"status": "no_abstract", "title": paper.title, "reason": "Abstract missing in DB"}

            # Return data for the LLM to judge
            return {
                "status": "found",
                "real_title": paper.title,
                "real_abstract": abstract,
                "citation_count": paper.citationCount,
                "url": paper.url
            }

        except Exception as e:
            logger.error(f"S2 Search failed: {e}")
            return {"status": "error", "reason": str(e)}

citation_verifier = CitationVerifierService()