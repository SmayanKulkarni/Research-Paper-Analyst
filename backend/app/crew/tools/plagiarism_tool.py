from crewai.tools import tool

from app.services.plagiarism import check_plagiarism_with_fallback


@tool("Plagiarism and Similarity Checker")
def plagiarism_tool(text: str):
    """
    Check a block of academic text for semantic plagiarism, paraphrasing,
    and overlap with previously indexed papers in Pinecone.

    Returns a JSON-serializable list of matches with:
      - source_id, source_title, source_url
      - similarity score
      - source_excerpt, user_excerpt
    """
    # Use the fallback-enabled plagiarism check which will crawl for similar papers if none are found.
    matches = check_plagiarism_with_fallback(text, fallback_to_crawl=True, max_papers_to_crawl=5)
    return [m.dict() for m in matches]
