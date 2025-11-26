from crewai.tools import tool

from app.services.plagiarism import check_plagiarism_with_discovery


@tool("Plagiarism and Similarity Checker")
def plagiarism_tool(text: str):
    """
    Check a block of academic text for semantic plagiarism, paraphrasing,
    and overlap with previously indexed papers in Pinecone.
    
    If no matches are found in the vector store, uses embedding-based similarity
    to discover related papers from arXiv for additional analysis.

    Returns a JSON-serializable list of matches with:
      - source_id, source_title, source_url
      - similarity score
      - source_excerpt, user_excerpt
    """
    # Use discovery-enabled plagiarism check: first checks Pinecone, then falls back to
    # embedding-based discovery of related arXiv papers
    matches = check_plagiarism_with_discovery(text, enable_discovery=True, discovery_top_k=5)
    return [m.dict() for m in matches]
