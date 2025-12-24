"""
Citation Resolver & Validator Service

- Extract numbered citations and reference entries from paper text
- Resolve arXiv IDs from references and download PDFs when available
- Parse cited PDFs and embed sections
- Validate citations against claim contexts using a checklist
"""

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import arxiv

from app.config import get_settings
from app.utils.logging import logger
from app.services.embeddings import embed_texts_numpy, compute_similarity
from app.services.pdf_parser_layout import parse_pdf_to_markdown

settings = get_settings()

# Lazy-load Pinecone service
_pinecone_service = None

def _get_pinecone_service():
    """Get Pinecone service; returns None if unavailable."""
    global _pinecone_service
    if _pinecone_service is None:
        try:
            from app.services.pinecone_client import pinecone_service
            _pinecone_service = pinecone_service
        except Exception as e:
            logger.debug(f"Pinecone unavailable: {e}")
            _pinecone_service = False
    return _pinecone_service if _pinecone_service else None

ARXIV_ID_PATTERN = re.compile(r"(?:arXiv:\s*)?(\d{4}\.\d{4,5})(?:v\d+)?", re.IGNORECASE)
DOI_PATTERN = re.compile(r"doi:\s*(10\.[^\s/]+/[^\s]+)", re.IGNORECASE)


@dataclass
class ReferenceEntry:
    number: int
    text: str
    arxiv_id: Optional[str] = None
    doi: Optional[str] = None
    title: Optional[str] = None
    year: Optional[int] = None


@dataclass
class CitationUse:
    citation_number: int
    claim_context: str
    reference: Optional[ReferenceEntry]
    used_section_title: Optional[str]
    support_score: float
    checklist: Dict[str, Any]
    suggestions: List[str]


class CitationResolver:
    def __init__(self, storage_root: Optional[str] = None):
        self.storage_root = storage_root or settings.STORAGE_ROOT
        os.makedirs(self.storage_root, exist_ok=True)

    def extract_references(self, full_text: str) -> List[ReferenceEntry]:
        """Extract numbered references from the References section."""
        refs_section_match = re.search(r"\n\s*(References|Bibliography)\s*\n", full_text, re.IGNORECASE)
        if not refs_section_match:
            logger.info("References section not found")
            return []
        start = refs_section_match.end()
        refs_text = full_text[start:]
        # Stop at next major section heuristic
        stop_match = re.search(r"\n\s*(Appendix|Acknowledg(e)?ments|Supplementary|Conclusion)\s*\n", refs_text, re.IGNORECASE)
        if stop_match:
            refs_text = refs_text[:stop_match.start()]
        entries: List[ReferenceEntry] = []
        # Split by lines starting with [n] or n.
        for m in re.finditer(r"^(\s*\[?(\d+)\]?)[\s.:\-]+(.+)$", refs_text, re.MULTILINE):
            num = int(m.group(2))
            text = m.group(3).strip()
            arx = None
            doi = None
            arx_m = ARXIV_ID_PATTERN.search(text)
            if arx_m:
                arx = arx_m.group(1)
            doi_m = DOI_PATTERN.search(text)
            if doi_m:
                doi = doi_m.group(1)
            # Title heuristic: content inside quotes or before first period
            title = None
            q_m = re.search(r"\“([^\”]+)\”|\"([^\"]+)\"", text)
            if q_m:
                title = q_m.group(1) or q_m.group(2)
            else:
                title = text.split(".")[0][:200]
            # Year heuristic: last 4-digit year
            year = None
            y_m = re.search(r"(20\d{2}|19\d{2})", text)
            if y_m:
                try:
                    year = int(y_m.group(1))
                except Exception:
                    year = None
            entries.append(ReferenceEntry(number=num, text=text, arxiv_id=arx, doi=doi, title=title, year=year))
        return entries

    def extract_citation_occurrences(self, full_text: str) -> List[Tuple[int, int]]:
        """Return list of (number, position) for in-text citations like [12], [3-5], [2,4]."""
        occ: List[Tuple[int, int]] = []
        for m in re.finditer(r"\[(\d+(?:\s*[-–,]\s*\d+)*)\]", full_text):
            span = m.span()
            raw = m.group(1)
            # Expand ranges and comma lists
            parts = re.split(r"\s*,\s*", raw)
            nums: List[int] = []
            for p in parts:
                if re.search(r"[-–]", p):
                    a, b = re.split(r"[-–]", p)
                    try:
                        a_i, b_i = int(a.strip()), int(b.strip())
                        nums.extend(list(range(min(a_i, b_i), max(a_i, b_i)+1)))
                    except Exception:
                        continue
                else:
                    try:
                        nums.append(int(p.strip()))
                    except Exception:
                        continue
            for n in nums:
                occ.append((n, span[0]))
        return occ

    def get_claim_context(self, full_text: str, pos: int, window: int = 400) -> str:
        """Slice ±window chars around citation position; clip at boundaries."""
        start = max(0, pos - window)
        end = min(len(full_text), pos + window)
        ctx = full_text[start:end]
        return ctx.strip()

    def download_arxiv_pdf(self, arxiv_id: str, base_dir: str) -> Optional[str]:
        try:
            os.makedirs(base_dir, exist_ok=True)
            search = arxiv.Search(id_list=[arxiv_id])
            paper = next(search.results(), None)
            if not paper:
                return None
            filename = f"{arxiv_id}.pdf"
            out_path = os.path.join(base_dir, filename)
            if not os.path.exists(out_path):
                paper.download_pdf(dirpath=base_dir, filename=filename)
            return out_path
        except Exception as e:
            logger.warning(f"Failed to download arXiv {arxiv_id}: {e}")
            return None

    def analyze_citation(self, claim_ctx: str, cited_pdf_path: Optional[str]) -> Tuple[Optional[str], float]:
        """Return (best_section_title, support_score) by comparing claim context to cited sections."""
        if not cited_pdf_path or not os.path.exists(cited_pdf_path):
            return (None, 0.0)
        try:
            parsed = parse_pdf_to_markdown(cited_pdf_path)
            text = parsed.get("text") or ""
            if not text:
                return (None, 0.0)
            # Split into rough sections by markdown headings or blank lines
            sections: List[Tuple[str, str]] = []
            current_title = "Document"
            buf: List[str] = []
            for line in text.splitlines():
                if re.match(r"^#+\s+", line):
                    # Commit previous
                    if buf:
                        sections.append((current_title, "\n".join(buf)))
                        buf = []
                    current_title = re.sub(r"^#+\s+", "", line).strip()
                else:
                    buf.append(line)
            if buf:
                sections.append((current_title, "\n".join(buf)))
            if not sections:
                sections = [("Document", text)]
            # Embed claim and sections
            claim_vec = embed_texts_numpy([claim_ctx])[0]
            sec_texts = [s[1] for s in sections]
            sec_vecs = embed_texts_numpy(sec_texts)
            # Compute similarities
            sims = [compute_similarity(claim_vec, v) for v in sec_vecs]
            best_idx = int(max(range(len(sims)), key=lambda i: sims[i])) if sims else 0
            best_title = sections[best_idx][0]
            support_score = float(sims[best_idx]) if sims else 0.0
            return (best_title, support_score)
        except Exception as e:
            logger.warning(f"Cited PDF analysis failed: {e}")
            return (None, 0.0)

    def checklist_verdict(self, claim_ctx: str, ref: ReferenceEntry, support_score: float) -> Dict[str, Any]:
        """Apply the quick checklist; return structured verdict."""
        verdict: Dict[str, Any] = {}
        verdict["supports_claim"] = support_score >= 0.25
        verdict["source_credible"] = bool(ref.arxiv_id)  # arXiv as credible preprint
        verdict["fair_representation"] = support_score >= 0.2
        verdict["proper_formatting"] = True  # Heuristic: numbered + entry exists
        verdict["current_and_accessible"] = (ref.year is None or ref.year >= 2018) and bool(ref.arxiv_id)
        verdict["support_score"] = round(support_score, 3)
        verdict["year"] = ref.year
        verdict["arxiv_id"] = ref.arxiv_id
        verdict["doi"] = ref.doi
        verdict["title"] = ref.title
        return verdict

    def suggest_improvements(self, verdict: Dict[str, Any], ref: Optional[ReferenceEntry] = None) -> List[str]:
        """Provide suggestions if support or representation are weak; query Pinecone for alternatives."""
        suggestions: List[str] = []
        if not verdict.get("supports_claim"):
            suggestions.append("The cited source may not strongly support the claim; consider citing the most relevant section explicitly or choosing a source with closer methodological alignment.")
        if not verdict.get("fair_representation"):
            suggestions.append("Ensure the claim accurately reflects the cited source's findings; avoid over-claiming beyond the paper's results.")
        if not verdict.get("current_and_accessible"):
            suggestions.append("Consider citing a more recent or accessible version (e.g., newer arXiv version or journal publication with DOI).")
        
        # Query Pinecone for alternative papers if weak support
        if not verdict.get("supports_claim") and ref and ref.title:
            try:
                pc_svc = _get_pinecone_service()
                if pc_svc:
                    # Embed the reference title for semantic search
                    ref_vec = embed_texts_numpy([ref.title])[0].tolist()
                    matches = pc_svc.query_hybrid(dense_vector=ref_vec, top_k=3)
                    if matches:
                        alt_titles = [m.get('metadata', {}).get('title', 'Unknown') for m in matches[:3] if m.get('metadata', {}).get('title')]
                        if alt_titles:
                            alts_str = "; ".join(alt_titles[:2])
                            suggestions.append(f"Consider alternative approaches available in the knowledge base: {alts_str}")
            except Exception as e:
                logger.debug(f"Pinecone alternative search failed: {e}")
        
        return suggestions

    def validate_all(self, full_text: str, file_tag: str = "paper") -> List[CitationUse]:
        refs = self.extract_references(full_text)
        refs_by_num: Dict[int, ReferenceEntry] = {r.number: r for r in refs}
        occs = self.extract_citation_occurrences(full_text)
        results: List[CitationUse] = []
        base_dir = os.path.join(self.storage_root, "downloads", "citations", file_tag)
        os.makedirs(base_dir, exist_ok=True)
        for num, pos in occs:
            ref = refs_by_num.get(num)
            ctx = self.get_claim_context(full_text, pos)
            cited_pdf = None
            if ref and ref.arxiv_id:
                cited_pdf = self.download_arxiv_pdf(ref.arxiv_id, base_dir)
            best_title, score = self.analyze_citation(ctx, cited_pdf)
            verdict = self.checklist_verdict(ctx, ref or ReferenceEntry(number=num, text=""), score)
            suggestions = self.suggest_improvements(verdict, ref)
            results.append(CitationUse(
                citation_number=num,
                claim_context=ctx,
                reference=ref,
                used_section_title=best_title,
                support_score=score,
                checklist=verdict,
                suggestions=suggestions,
            ))
        # Deduplicate by citation number keeping highest support
        best_by_num: Dict[int, CitationUse] = {}
        for cu in results:
            prev = best_by_num.get(cu.citation_number)
            if not prev or cu.support_score > prev.support_score:
                best_by_num[cu.citation_number] = cu
        return list(sorted(best_by_num.values(), key=lambda x: x.citation_number))


def get_citation_resolver() -> CitationResolver:
    return CitationResolver()
