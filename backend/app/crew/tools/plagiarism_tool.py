import json
from crewai.tools import tool
from app.services.plagiarism import check_plagiarism

@tool("Plagiarism Checker")
def plagiarism_tool(text: str):
    """
    Check a block of academic text for semantic plagiarism using hybrid search.
    Returns a formatted text report of matches.
    """
    matches = check_plagiarism(text)
    
    if not matches:
        return "No plagiarism matches found in the database."
    
    # Format the output nicely for the Agent to read
    report_lines = ["--- PLAGIARISM DETECTED ---"]
    for m in matches:
        # Check for error keys first
        if "error" in m:
            return f"Error during check: {m['error']}"
            
        score = m.get('similarity_score', 0)
        source = m.get('source_title', 'Unknown Source')
        url = m.get('source_url', 'No URL')
        segment = m.get('suspicious_segment', '')
        
        report_lines.append(f"• MATCH ({score:.2f}): {source}")
        report_lines.append(f"  URL: {url}")
        report_lines.append(f"  TEXT: \"{segment}\"")
        report_lines.append("")
        
    return "\n".join(report_lines)