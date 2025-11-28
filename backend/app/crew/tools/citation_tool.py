from crewai.tools import tool
from typing import Dict
from app.services.citation_verifier import citation_verifier

@tool("Citation Integrity Checker")
def verify_citation_integrity(claim_text: str, reference_string: str):
    """
    Verifies if a specific claim is supported by the cited paper.
    
    Args:
        claim_text: The sentence from the paper making a claim (e.g., "Transformers are fast [1].")
        reference_string: The full reference string from the bibliography for [1] (e.g., "Vaswani et al., Attention is all you need...")
    """
    result = citation_verifier.verify_claim(claim_text, reference_string)
    
    if result["status"] != "found":
        return f"Could not verify. Reason: {result.get('reason')}"
        
    return (
        f"--- CITATION DATA ---\n"
        f"Found Paper: {result['real_title']}\n"
        f"Citations: {result['citation_count']}\n"
        f"Abstract: {result['real_abstract']}\n\n"
        f"INSTRUCTION FOR AGENT: Compare the 'Abstract' above with the user's 'claim_text'. "
        f"Does the abstract support the claim? If not, flag it."
    )