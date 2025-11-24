from crewai.tools import tool

from app.services.plagiarism import check_plagiarism


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
    matches = check_plagiarism(text)
    return [m.dict() for m in matches]
