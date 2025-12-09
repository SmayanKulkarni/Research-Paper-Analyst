from crewai.tools import tool
from groq import Groq
from typing import List, Dict, Any

from app.services.plagiarism import check_plagiarism
from app.config import get_settings
from app.utils.logging import logger

settings = get_settings()


def _web_search_plagiarism(text_chunks: List[str], max_chunks: int = 5) -> List[Dict[str, Any]]:
    """
    Use Groq's browser_search to check text chunks for plagiarism.
    
    Args:
        text_chunks: List of text segments to check
        max_chunks: Maximum number of chunks to search (to limit API calls)
    
    Returns:
        List of potential plagiarism matches from web search
    """
    client = Groq(api_key=settings.GROQ_API_KEY)
    model = "openai/gpt-oss-20b"  # Supports browser_search
    
    web_matches = []
    chunks_to_check = text_chunks[:max_chunks]
    
    for i, chunk in enumerate(chunks_to_check):
        # Create a search query from key phrases in the chunk
        # Take first 100 chars as search query
        search_query = chunk[:150].replace('\n', ' ').strip()
        
        try:
            resp = client.chat.completions.create(
                messages=[
                    {
                        "role": "system", 
                        "content": (
                            "You are a plagiarism detection assistant. Search the web for "
                            "text that matches or closely resembles the given passage. "
                            "If you find matching content, report the source URL and title. "
                            "Respond in JSON format: {\"found\": true/false, \"sources\": [{\"title\": \"...\", \"url\": \"...\", \"similarity\": \"high/medium/low\"}]}"
                        )
                    },
                    {
                        "role": "user", 
                        "content": f'Search for text similar to: "{search_query}"'
                    }
                ],
                model=model,
                temperature=0.3,
                max_completion_tokens=500,
                tool_choice="auto",
                tools=[{"type": "browser_search"}],
            )
            
            content = resp.choices[0].message.content
            if content:
                # Try to parse JSON response
                import json
                try:
                    result = json.loads(content)
                    if result.get("found") and result.get("sources"):
                        for src in result["sources"]:
                            similarity_map = {"high": 0.9, "medium": 0.75, "low": 0.5}
                            web_matches.append({
                                "chunk_index": i,
                                "suspicious_segment": chunk[:200] + "...",
                                "source_title": src.get("title", "Web Source"),
                                "source_url": src.get("url", ""),
                                "similarity_score": similarity_map.get(src.get("similarity", "medium"), 0.7),
                                "detection_method": "WebSearch"
                            })
                except json.JSONDecodeError:
                    # If not JSON, check if response mentions finding similar content
                    if "found" in content.lower() or "similar" in content.lower():
                        logger.info(f"Web search found potential match for chunk {i}")
                        
        except Exception as e:
            logger.warning(f"Web search failed for chunk {i}: {e}")
            continue
    
    return web_matches


def _extract_key_chunks(text: str, max_chunks: int = 5) -> List[str]:
    """
    Extract key chunks from text for plagiarism checking.
    Focus on introduction, conclusion, and unique passages.
    """
    words = text.split()
    total_words = len(words)
    
    if total_words < 100:
        return [text]
    
    chunks = []
    chunk_size = 150  # ~150 words per chunk
    
    # Get intro (first chunk)
    chunks.append(" ".join(words[:chunk_size]))
    
    # Get a few middle sections
    if total_words > chunk_size * 3:
        mid_start = total_words // 3
        chunks.append(" ".join(words[mid_start:mid_start + chunk_size]))
        
        mid_start2 = (total_words * 2) // 3
        chunks.append(" ".join(words[mid_start2:mid_start2 + chunk_size]))
    
    # Get conclusion (last chunk)
    if total_words > chunk_size * 2:
        chunks.append(" ".join(words[-chunk_size:]))
    
    return chunks[:max_chunks]


@tool("Plagiarism and Similarity Checker")
def plagiarism_tool(text: str):
    """
    Run comprehensive plagiarism check using both vector similarity and web search.
    Returns matches from both the academic paper database and live web search.
    """
    # Truncate text for processing
    text = text[:50000] if len(text) > 50000 else text
    
    all_matches = []
    
    # Method 1: Vector-based similarity check against paper database
    try:
        db_matches = check_plagiarism(text)
        for m in db_matches:
            m["detection_method"] = "VectorDB"
        all_matches.extend(db_matches)
        logger.info(f"Vector DB check found {len(db_matches)} matches")
    except Exception as e:
        logger.warning(f"Vector DB plagiarism check failed: {e}")
    
    # Method 2: Web search for key passages
    try:
        key_chunks = _extract_key_chunks(text, max_chunks=3)
        web_matches = _web_search_plagiarism(key_chunks, max_chunks=3)
        all_matches.extend(web_matches)
        logger.info(f"Web search check found {len(web_matches)} matches")
    except Exception as e:
        logger.warning(f"Web search plagiarism check failed: {e}")
    
    # Compute summary
    max_score = max([m.get("similarity_score", 0.0) for m in all_matches], default=0.0)
    plagiarism_detected = bool(all_matches) and max_score >= 0.75

    # Normalize and deduplicate matches
    seen_urls = set()
    normalized_matches = []
    for m in all_matches:
        url = m.get("source_url", "")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        normalized_matches.append({
            "similarity_score": float(m.get("similarity_score", 0.0)),
            "source_title": m.get("source_title", "Unknown"),
            "source_url": url,
            "suspicious_segment": m.get("suspicious_segment", ""),
            "detection_method": m.get("detection_method", "Unknown"),
        })

    assessment = (
        "High Risk" if max_score >= 0.9 else
        "Suspicious" if max_score >= 0.75 else
        "Low Risk" if max_score >= 0.5 else
        "Safe"
    )

    return {
        "plagiarism_detected": plagiarism_detected,
        "max_similarity_score": float(max_score),
        "matches": normalized_matches[:10],  # Limit to top 10 matches
        "assessment": assessment,
        "methods_used": ["VectorDB", "WebSearch"],
    }
