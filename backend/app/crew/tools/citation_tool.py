"""
Citation Reference Checker Tool

Simple tool that checks if all citations in a paper's reference list
are actually cited in the paper content, and vice versa.
No external API calls - purely internal consistency checking.
"""

import re
from crewai.tools import tool
from typing import Dict, List, Tuple, Set
from app.utils.logging import logger


def _extract_numbered_citations(text: str) -> Set[int]:
    """
    Extract all numbered citations like [1], [2], [1,2], [1-3], etc.
    """
    citations = set()
    
    # Match [1], [2], etc.
    single_matches = re.findall(r'\[(\d+)\]', text)
    for m in single_matches:
        citations.add(int(m))
    
    # Match [1,2,3] or [1, 2, 3]
    multi_matches = re.findall(r'\[([\d,\s]+)\]', text)
    for m in multi_matches:
        nums = re.findall(r'\d+', m)
        for n in nums:
            citations.add(int(n))
    
    # Match [1-3] ranges
    range_matches = re.findall(r'\[(\d+)-(\d+)\]', text)
    for start, end in range_matches:
        for i in range(int(start), int(end) + 1):
            citations.add(i)
    
    return citations


def _extract_author_year_citations(text: str) -> Set[str]:
    """
    Extract author-year citations like (Smith et al., 2020), (Jones, 2019), etc.
    """
    citations = set()
    
    # Match (Author et al., YYYY) or (Author, YYYY)
    patterns = [
        r'\(([A-Z][a-z]+(?:\s+et\s+al\.)?),?\s*(\d{4})\)',
        r'\(([A-Z][a-z]+)\s+and\s+([A-Z][a-z]+),?\s*(\d{4})\)',
        r'([A-Z][a-z]+(?:\s+et\s+al\.)?)\s*\((\d{4})\)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if isinstance(match, tuple):
                citations.add(' '.join(match))
            else:
                citations.add(match)
    
    return citations


def _extract_references_section(text: str) -> Tuple[str, List[Tuple[int, str]]]:
    """
    Extract the references section and parse individual references.
    Returns (references_text, list_of_individual_references)
    """
    # Common reference section headers
    headers = [
        r'(?:^|\n)\s*References?\s*\n',
        r'(?:^|\n)\s*REFERENCES?\s*\n',
        r'(?:^|\n)\s*Bibliography\s*\n',
        r'(?:^|\n)\s*BIBLIOGRAPHY\s*\n',
        r'(?:^|\n)\s*Works\s+Cited\s*\n',
        r'(?:^|\n)\s*Literature\s+Cited\s*\n',
    ]
    
    ref_start = -1
    for header in headers:
        match = re.search(header, text, re.IGNORECASE)
        if match:
            ref_start = match.end()
            break
    
    if ref_start == -1:
        return "", []
    
    references_text = text[ref_start:]
    
    # Try to parse individual references
    references: List[Tuple[int, str]] = []
    
    # Numbered references: [1] Author...
    numbered_refs = re.findall(r'\[(\d+)\]\s*([^\[]+?)(?=\[\d+\]|$)', references_text, re.DOTALL)
    if numbered_refs:
        for num, ref_text in numbered_refs:
            references.append((int(num), ref_text.strip()))
        return references_text, references
    
    # Numbered references without brackets: 1. Author...
    dotted_refs = re.findall(r'^(\d+)\.\s+(.+?)(?=^\d+\.|$)', references_text, re.MULTILINE | re.DOTALL)
    if dotted_refs:
        for num, ref_text in dotted_refs:
            references.append((int(num), ref_text.strip()))
        return references_text, references
    
    # Try splitting by double newlines for author-year style
    chunks = re.split(r'\n\s*\n', references_text)
    for i, chunk in enumerate(chunks):
        chunk = chunk.strip()
        if chunk and len(chunk) > 20:  # Reasonable reference length
            references.append((i + 1, chunk))
    
    return references_text, references


def _get_content_without_references(text: str) -> str:
    """
    Get the paper content excluding the references section.
    """
    headers = [
        r'(?:^|\n)\s*References?\s*\n',
        r'(?:^|\n)\s*REFERENCES?\s*\n',
        r'(?:^|\n)\s*Bibliography\s*\n',
        r'(?:^|\n)\s*BIBLIOGRAPHY\s*\n',
    ]
    
    for header in headers:
        match = re.search(header, text, re.IGNORECASE)
        if match:
            return text[:match.start()]
    
    return text


@tool("Citation Reference Checker")
def check_citation_references(paper_text: str) -> str:
    """
    Check if all citations in the paper are properly referenced and vice versa.
    
    This tool analyzes:
    1. Which numbered citations [1], [2], etc. appear in the paper content
    2. Which references are listed in the References section
    3. Whether all cited references exist in the reference list
    4. Whether all references in the list are actually cited
    
    Args:
        paper_text: The full text of the research paper
        
    Returns:
        A detailed report of citation-reference consistency
    """
    try:
        # Get content without references section
        content = _get_content_without_references(paper_text)
        
        # Extract citations from content
        numbered_citations = _extract_numbered_citations(content)
        author_year_citations = _extract_author_year_citations(content)
        
        # Extract references section
        ref_text, references = _extract_references_section(paper_text)
        
        # Build report
        lines = []
        lines.append("=" * 60)
        lines.append("CITATION-REFERENCE CONSISTENCY CHECK")
        lines.append("=" * 60)
        lines.append("")
        
        # Citation style detection
        if numbered_citations and not author_year_citations:
            citation_style = "Numbered [1], [2], etc."
        elif author_year_citations and not numbered_citations:
            citation_style = "Author-Year (Smith, 2020)"
        elif numbered_citations and author_year_citations:
            citation_style = "Mixed (both numbered and author-year)"
        else:
            citation_style = "Unable to detect"
        
        lines.append(f"Citation Style Detected: {citation_style}")
        lines.append("")
        
        # References section found?
        if not ref_text:
            lines.append("⚠️ WARNING: No References section found!")
            lines.append("   The paper may be missing a references section,")
            lines.append("   or it uses a non-standard section name.")
            lines.append("")
            lines.append("=" * 60)
            return "\n".join(lines)
        
        # Statistics
        lines.append("## STATISTICS")
        lines.append(f"- Citations found in text: {len(numbered_citations)}")
        lines.append(f"- References in reference list: {len(references)}")
        lines.append("")
        
        # For numbered citations, check consistency
        if numbered_citations:
            ref_numbers = {num for num, _ in references}
            
            # Citations without references
            missing_refs = numbered_citations - ref_numbers
            if missing_refs:
                lines.append("## ❌ CITATIONS WITHOUT REFERENCES")
                lines.append("These citations appear in the text but have no corresponding reference:")
                for num in sorted(missing_refs):
                    lines.append(f"   - Citation [{num}] - NOT FOUND in references")
                lines.append("")
            else:
                lines.append("## ✅ All citations have corresponding references")
                lines.append("")
            
            # References not cited
            uncited_refs = ref_numbers - numbered_citations
            if uncited_refs:
                lines.append("## ⚠️ UNCITED REFERENCES")
                lines.append("These references exist but are never cited in the text:")
                for num in sorted(uncited_refs):
                    # Find the reference text
                    ref_text_found = next((r[1][:100] for r in references if r[0] == num), "")
                    lines.append(f"   - Reference [{num}]: {ref_text_found}...")
                lines.append("")
            else:
                lines.append("## ✅ All references are cited in the text")
                lines.append("")
            
            # Citation numbering gaps
            if numbered_citations:
                max_citation = max(numbered_citations)
                expected = set(range(1, max_citation + 1))
                gaps = expected - numbered_citations
                if gaps:
                    lines.append("## ⚠️ CITATION NUMBERING GAPS")
                    lines.append(f"Expected citations 1 to {max_citation}, but these are missing:")
                    for num in sorted(gaps):
                        lines.append(f"   - [{num}] not used")
                    lines.append("")
        
        # Reference list analysis
        if references:
            lines.append("## REFERENCE LIST SUMMARY")
            lines.append(f"Total references: {len(references)}")
            
            # Check for common issues
            issues = []
            for num, ref_text_item in references:
                if len(ref_text_item) < 30:
                    issues.append(f"[{num}] Very short reference (may be incomplete)")
                if not re.search(r'\d{4}', ref_text_item):
                    issues.append(f"[{num}] No year found in reference")
            
            if issues:
                lines.append("\nPotential issues in references:")
                for issue in issues[:10]:  # Limit to first 10
                    lines.append(f"   - {issue}")
                if len(issues) > 10:
                    lines.append(f"   ... and {len(issues) - 10} more issues")
            lines.append("")
        
        # Final assessment
        lines.append("## FINAL ASSESSMENT")
        
        issues_count = 0
        if numbered_citations:
            ref_numbers = {num for num, _ in references}
            issues_count += len(numbered_citations - ref_numbers)  # Missing refs
            issues_count += len(ref_numbers - numbered_citations)  # Uncited refs
        
        if issues_count == 0:
            lines.append("✅ GOOD: All citations and references are properly linked.")
        elif issues_count <= 3:
            lines.append("⚠️ MINOR ISSUES: A few citation-reference mismatches found.")
        else:
            lines.append("❌ NEEDS ATTENTION: Multiple citation-reference issues found.")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Citation check error: {e}")
        return (
            "=" * 60 + "\n"
            "CITATION-REFERENCE CHECK\n"
            "=" * 60 + "\n\n"
            f"Error during analysis: {str(e)[:200]}\n\n"
            "The citation checking encountered an error.\n"
            "Manual review of citations and references is recommended.\n"
            "=" * 60
        )
