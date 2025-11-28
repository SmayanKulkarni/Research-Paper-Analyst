import re
from typing import List, Dict, Optional, Any
from semanticscholar import SemanticScholar
from app.config import get_settings
from app.utils.logging import logger

settings = get_settings()

class CitationVerifierService:
    def __init__(self):
        # Initialize Semantic Scholar Client
        self.sch = SemanticScholar(timeout=10)

    def extract_claims_with_citations(self, text: str) -> List[Dict[str, str]]:
        """
        Extract sentences that contain citations like [1], [12], (Author, 2020).
        """
        numeric_pattern = r'(\.?[^\.]*?\[\d+(?:[–,-]\d+)*\][^\.]*\.)'
        matches = re.findall(numeric_pattern, text)
        claims = []
        
        for match in matches:
            clean_claim = match.strip()
            ref_ids = re.findall(r'\[(\d+)\]', clean_claim)
            
            if ref_ids:
                claims.append({
                    "claim_text": clean_claim,
                    "ref_id": ref_ids[0]
                })
        return claims

    def resolve_reference_title(self, text: str, ref_id: str) -> Optional[str]:
        """
        Finds the References section and looks up what "[1]" actually is.
        """
        ref_section_match = re.search(r'(?i)references\s*\n', text)
        if not ref_section_match: return None
            
        ref_text = text[ref_section_match.end():]
        pattern = re.escape(f"[{ref_id}]") + r'\s*(.*?)(?=\n\[\d+\]|\Z)'
        match = re.search(pattern, ref_text, re.DOTALL)
        
        if match:
            return match.group(1).replace('\n', ' ').strip()
        return None

    def verify_claim(self, claim: str, ref_title_blob: str) -> Dict[str, Any]:
        try:
            # Heuristic: search by the first 15 words of the reference string
            search_query = " ".join(ref_title_blob.split()[:15]) 
            results = self.sch.search_paper(search_query, limit=1)
            
            if not results:
                return {"status": "not_found", "reason": "Paper not found on Semantic Scholar"}
            
            paper = results[0]
            abstract = paper.abstract
            
            if not abstract:
                return {"status": "no_abstract", "title": paper.title, "reason": "Abstract missing in DB"}

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