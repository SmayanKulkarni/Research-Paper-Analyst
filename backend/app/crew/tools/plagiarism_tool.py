from crewai.tools import tool

from app.services.plagiarism import check_plagiarism


@tool("Plagiarism and Similarity Checker")
def plagiarism_tool(text: str):
  """
  Run the hybrid plagiarism check and return a schema that matches PlagiarismOutput
  so the agent doesn't need to transform tool output.
  """
  matches = check_plagiarism(text)  # List[Dict[str, Any]] with keys from plagiarism engine

  # Compute summary
  max_score = max([m.get("similarity_score", 0.0) for m in matches], default=0.0)
  plagiarism_detected = bool(matches) and max_score >= 0.75

  # Map to PlagiarismMatch schema expected by PlagiarismOutput
  normalized_matches = []
  for m in matches:
    normalized_matches.append({
      "similarity_score": float(m.get("similarity_score", 0.0)),
      "source_title": m.get("source_title", "Unknown"),
      "source_url": m.get("source_url", ""),
      "suspicious_segment": m.get("suspicious_segment", ""),
    })

  assessment = (
    "High Risk" if max_score >= 0.9 else
    "Suspicious" if max_score >= 0.75 else
    "Safe"
  )

  return {
    "plagiarism_detected": plagiarism_detected,
    "max_similarity_score": float(max_score),
    "matches": normalized_matches,
    "assessment": assessment,
  }
