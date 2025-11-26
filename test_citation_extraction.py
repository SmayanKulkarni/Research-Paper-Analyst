#!/usr/bin/env python3
"""
Test script to verify citation extraction improvements.

This demonstrates the multi-strategy citation extraction:
1. References section with [NUM] citations
2. Inline [NUM] citations throughout text
3. Standalone arXiv/DOI URLs
"""

from app.services.citation_extractor import extract_citations_from_text, filter_arxiv_citations

# Test case 1: Traditional References section
test_text_1 = """
Some research content here.

References
[1] Smith et al., "Deep Learning Models", arXiv:2101.12345, 2021.
[2] Johnson, K., "Neural Networks", Journal of ML, 2020. https://doi.org/10.1234/example
[3] Brown & Lee, "Computer Vision", 2019.
"""

print("=" * 60)
print("TEST 1: Traditional References Section with [NUM]")
print("=" * 60)
citations = extract_citations_from_text(test_text_1)
arxiv_citations = filter_arxiv_citations(citations)
print(f"Extracted: {len(citations)} citations")
print(f"Filtered to arXiv/DOI: {len(arxiv_citations)} citations")
for c in arxiv_citations:
    print(f"  - arXiv: {c.get('arxiv_id')}, DOI: {c.get('doi')}, URL: {c.get('url')}")

# Test case 2: Inline citations
test_text_2 = """
This research builds on [1] foundational work in deep learning [2].

The key insight from [3] shows that arXiv:2202.54321 is crucial.

More work [4] uses https://doi.org/10.5555/test.

References
[1] Research A
[2] Research B
[3] Research C citing arXiv:2202.54321
[4] Research D with DOI
"""

print("\n" + "=" * 60)
print("TEST 2: Inline Citations with Context")
print("=" * 60)
citations = extract_citations_from_text(test_text_2)
arxiv_citations = filter_arxiv_citations(citations)
print(f"Extracted: {len(citations)} citations")
print(f"Filtered to arXiv/DOI: {len(arxiv_citations)} citations")
for c in arxiv_citations:
    print(f"  - arXiv: {c.get('arxiv_id')}, DOI: {c.get('doi')}, URL: {c.get('url')}")

# Test case 3: Standalone URLs
test_text_3 = """
Some research content mentioning:
- https://arxiv.org/abs/2303.08774
- https://doi.org/10.1234/nature.2023
- https://arxiv.org/pdf/2401.01234.pdf

No formal references section.
"""

print("\n" + "=" * 60)
print("TEST 3: Standalone arXiv/DOI URLs (No References Section)")
print("=" * 60)
citations = extract_citations_from_text(test_text_3)
arxiv_citations = filter_arxiv_citations(citations)
print(f"Extracted: {len(citations)} citations")
print(f"Filtered to arXiv/DOI: {len(arxiv_citations)} citations")
for c in arxiv_citations:
    print(f"  - arXiv: {c.get('arxiv_id')}, DOI: {c.get('doi')}, URL: {c.get('url')}")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print("""
The improved citation extractor now uses a 3-strategy approach:

STRATEGY 1: References Section
  - Looks for "References", "Bibliography", "Related Work" sections
  - Extracts [NUM] or numbered citations from that section
  - Most reliable for traditional academic papers

STRATEGY 2: Inline Citations
  - Finds [NUM] markers throughout the text
  - Extracts nearby context for arXiv/DOI information
  - Works for papers with less formal reference sections

STRATEGY 3: Standalone URLs
  - Finds arXiv and DOI URLs anywhere in the document
  - Works for papers with non-standard formatting
  - Useful as a fallback when other strategies fail

Results are then filtered to keep only citations with:
  - arXiv IDs
  - DOI URLs (can be resolved to papers)
  - Generic URLs pointing to papers

This ensures broader citation coverage across different PDF formats.
""")
