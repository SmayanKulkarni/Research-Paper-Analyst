"""
citation_extractor.py

Extract bibliography/references from research papers and resolve them to structured citation objects.
Identifies arXiv IDs, DOI links, and URLs from citation sections.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from app.utils.logging import logger


def _extract_arxiv_id(text: str) -> Optional[str]:
    """Extract arXiv ID from a citation text if present.
    
    Matches patterns like:
    - arXiv:2101.12345
    - arxiv.org/abs/2101.12345
    - arxiv.org/pdf/2101.12345.pdf
    """
    # Pattern 1: arXiv:YYMM.NNNNN
    match = re.search(r'arXiv[:\s]+(\d{4}\.\d{4,5})', text, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Pattern 2: arxiv.org/abs/YYMM.NNNNN
    match = re.search(r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})', text, re.IGNORECASE)
    if match:
        return match.group(1)
    
    return None


def _extract_doi(text: str) -> Optional[str]:
    """Extract DOI from citation text if present.
    
    Matches patterns like:
    - doi:10.XXXX/YYYY
    - https://doi.org/10.XXXX/YYYY
    """
    match = re.search(r'(?:doi[:\s]+|https?://doi\.org/)([^\s,\]]+)', text, re.IGNORECASE)
    if match:
        return match.group(1)
    
    return None


def _extract_url(text: str) -> Optional[str]:
    """Extract any URL from citation text."""
    match = re.search(r'https?://[^\s,\]]+', text)
    if match:
        return match.group(0)
    
    return None


def _extract_authors_and_title(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Attempt to extract authors and title from a single citation line.
    
    Heuristic: usually formatted as "Author et al., Title, Year" or similar.
    Look for patterns like:
    - "Smith, J., et al." or "Smith et al."
    - Title followed by year in parens or at end
    
    Returns (authors_str, title_str) if found, else (None, None).
    """
    # Remove URLs and arXiv IDs for cleaner parsing
    clean = re.sub(r'https?://\S+', '', text)
    clean = re.sub(r'arXiv[:\s]*\d{4}\.\d{4,5}', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'doi[:\s]+\S+', '', clean, flags=re.IGNORECASE)
    
    # Try to split on common delimiters (comma, period, dash)
    parts = re.split(r'[,.]', clean, maxsplit=2)
    
    authors = None
    title = None
    
    if len(parts) >= 1:
        potential_authors = parts[0].strip()
        # Check if this looks like authors (contains "et al" or multiple names)
        if 'et al' in potential_authors.lower() or ' and ' in potential_authors or len(potential_authors) < 150:
            authors = potential_authors
    
    if len(parts) >= 2:
        potential_title = parts[1].strip()
        # Title is usually between authors and year/venue
        if potential_title and len(potential_title) > 5 and len(potential_title) < 300:
            title = potential_title
    
    return authors, title


def extract_citations_from_text(text: str, max_citations: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Extract all citations from research paper text.
    
    Looks for:
    1. References/Bibliography section (most reliable)
    2. [1], [2], etc. inline citations throughout text
    3. Standalone arXiv/DOI URLs anywhere in the document
    4. Numbered reference lists (1. Citation)
    
    Returns list of citation dicts with structure:
    {
        "raw_text": str,
        "arxiv_id": Optional[str],
        "doi": Optional[str],
        "url": Optional[str],
        "authors": Optional[str],
        "title": Optional[str],
        "index": int,
    }
    """
    citations: List[Dict[str, Any]] = []
    
    # STRATEGY 1: Find and extract from References or Bibliography section
    ref_match = re.search(
        r'(?:^|\n)(?:REFERENCES|References|BIBLIOGRAPHY|Bibliography|References and Notes|RELATED WORK|Related Work)(?:\s*\n|$)',
        text,
        re.MULTILINE | re.IGNORECASE
    )
    
    if ref_match:
        # Extract text from References section to end of document
        ref_section = text[ref_match.end():]
        
        # Try splitting by bracketed numbers first [1], [2], etc.
        citation_pattern = r'\[\d+\]\s*(.+?)(?=\[\d+\]|$)'
        citation_matches = list(re.finditer(citation_pattern, ref_section, re.DOTALL))
        
        if citation_matches:
            for idx, match in enumerate(citation_matches):
                citation_text = match.group(1).strip()
                if not citation_text or len(citation_text) < 10:
                    continue
                
                arxiv_id = _extract_arxiv_id(citation_text)
                doi = _extract_doi(citation_text)
                url = _extract_url(citation_text)
                authors, title = _extract_authors_and_title(citation_text)
                
                citations.append({
                    "raw_text": citation_text[:500],
                    "arxiv_id": arxiv_id,
                    "doi": doi,
                    "url": url,
                    "authors": authors,
                    "title": title,
                    "index": idx,
                })
                
                if max_citations and len(citations) >= max_citations:
                    return citations
        
        # Fallback within References: try numbered list (1. Citation)
        if not citation_matches:
            citation_pattern = r'^\s*\d+\.\s+(.+?)(?=^\s*\d+\.|$)'
            citation_matches = list(re.finditer(citation_pattern, ref_section, re.MULTILINE | re.DOTALL))
            
            for idx, match in enumerate(citation_matches):
                citation_text = match.group(1).strip()
                if not citation_text or len(citation_text) < 10:
                    continue
                
                arxiv_id = _extract_arxiv_id(citation_text)
                doi = _extract_doi(citation_text)
                url = _extract_url(citation_text)
                authors, title = _extract_authors_and_title(citation_text)
                
                citations.append({
                    "raw_text": citation_text[:500],
                    "arxiv_id": arxiv_id,
                    "doi": doi,
                    "url": url,
                    "authors": authors,
                    "title": title,
                    "index": idx,
                })
                
                if max_citations and len(citations) >= max_citations:
                    return citations
    
    # STRATEGY 2: If no References section found, extract inline citations [1], [2], etc.
    # These appear throughout the text as [NUM]
    if not citations:
        logger.debug("No References section found; extracting inline citations from full text")
        
        # Find all inline [NUM] citation markers and their contexts
        inline_pattern = r'\[(\d+)\]'
        inline_matches = list(re.finditer(inline_pattern, text))
        
        if inline_matches:
            seen_numbers = set()
            for match in inline_matches:
                citation_num = int(match.group(1))
                if citation_num in seen_numbers:
                    continue
                seen_numbers.add(citation_num)
                
                # For inline citations, we can't easily extract the full citation text
                # But we can mark that this citation exists
                # Try to find nearby arXiv/DOI references
                context_start = max(0, match.start() - 200)
                context_end = min(len(text), match.end() + 200)
                context = text[context_start:context_end]
                
                arxiv_id = _extract_arxiv_id(context)
                doi = _extract_doi(context)
                url = _extract_url(context)
                
                if arxiv_id or doi or url:
                    citations.append({
                        "raw_text": context[:500],
                        "arxiv_id": arxiv_id,
                        "doi": doi,
                        "url": url,
                        "authors": None,
                        "title": None,
                        "index": citation_num,
                    })
                
                if max_citations and len(citations) >= max_citations:
                    return citations
    
    # STRATEGY 3: Standalone arXiv/DOI URLs anywhere in the document
    # (e.g., in footnotes, URLs listed separately, etc.)
    if not citations:
        logger.debug("No inline citations found; searching for standalone arXiv/DOI URLs")
        
        # Find all arXiv URLs
        arxiv_urls = re.finditer(r'https?://arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})', text)
        for idx, match in enumerate(arxiv_urls):
            arxiv_id = match.group(1)
            url = match.group(0)
            citations.append({
                "raw_text": url,
                "arxiv_id": arxiv_id,
                "doi": None,
                "url": url,
                "authors": None,
                "title": None,
                "index": len(citations),
            })
            
            if max_citations and len(citations) >= max_citations:
                return citations
        
        # Find all DOI URLs
        doi_urls = re.finditer(r'https?://doi\.org/([^\s,\]\)]+)', text)
        for idx, match in enumerate(doi_urls):
            doi = match.group(1)
            url = match.group(0)
            citations.append({
                "raw_text": url,
                "arxiv_id": None,
                "doi": doi,
                "url": url,
                "authors": None,
                "title": None,
                "index": len(citations),
            })
            
            if max_citations and len(citations) >= max_citations:
                return citations
    
    logger.info(f"Extracted {len(citations)} citations from text")
    return citations


def filter_arxiv_citations(citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter citations to keep only those that can be resolved to papers.
    
    Keeps:
    1. Citations with arXiv IDs
    2. Citations with arXiv URLs
    3. Citations with DOI URLs (can be resolved to arXiv if available)
    4. Generic URLs that might be papers (non-greedy, only https URLs from academic sources)
    
    Note: DOI resolution happens later in arxiv_finder.
    """
    resolvable_citations = []
    
    for c in citations:
        # Must have at least one identifier
        if c.get("arxiv_id"):
            resolvable_citations.append(c)
            continue
        
        url = c.get("url", "")
        
        # arXiv URLs (explicit arXiv reference)
        if url and 'arxiv' in url.lower():
            resolvable_citations.append(c)
            continue
        
        # DOI URLs (can be resolved later)
        if url and 'doi.org' in url.lower():
            resolvable_citations.append(c)
            continue
        
        # Explicit DOI field
        if c.get("doi"):
            resolvable_citations.append(c)
            continue
    
    logger.info(f"Filtered {len(citations)} citations down to {len(resolvable_citations)} with arXiv/DOI identifiers")
    return resolvable_citations
