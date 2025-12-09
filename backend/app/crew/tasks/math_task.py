"""
Math Review Task - Task for analyzing mathematical content in papers.

Analyzes equations, proofs, derivations, and mathematical reasoning.
"""

from crewai import Task, Agent
from typing import Optional


def create_math_review_task(
    agent: Agent,
    math_content: str,
    context_text: Optional[str] = None,
) -> Task:
    """
    Create a task for reviewing mathematical content.
    
    Args:
        agent: The Math Review Agent
        math_content: Extracted mathematical content (equations, proofs, etc.)
        context_text: Optional surrounding context for the math
    
    Returns:
        Task for math review
    """
    # Build the analysis prompt
    prompt_parts = [
        "Analyze the following mathematical content from a research paper.",
        "",
        "IMPORTANT: Complete this task in ONE attempt. DO NOT retry or request more information.",
        "If content is unclear, provide your best analysis and note limitations.",
        "",
        "=== MATHEMATICAL CONTENT ===",
        math_content[:15000] if len(math_content) > 15000 else math_content,  # Token limit
    ]
    
    if context_text:
        prompt_parts.extend([
            "",
            "=== SURROUNDING CONTEXT ===",
            context_text[:5000] if len(context_text) > 5000 else context_text,
        ])
    
    prompt_parts.extend([
        "",
        "=== ANALYSIS INSTRUCTIONS ===",
        "Provide a structured review covering:",
        "",
        "1. **Equation Correctness**: Are equations mathematically valid? Any obvious errors?",
        "2. **Derivation Logic**: Do derivations follow logically? Are steps justified?",
        "3. **Proof Completeness**: Are proofs complete and rigorous?",
        "4. **Notation Consistency**: Is mathematical notation used consistently?",
        "5. **Clarity**: Are mathematical explanations clear and understandable?",
        "6. **Potential Issues**: Any ambiguities, undefined terms, or missing assumptions?",
        "",
        "Format your response as:",
        "```",
        "## Math Review Summary",
        "",
        "### Overall Assessment",
        "[Brief summary of mathematical quality]",
        "",
        "### Equation Analysis",
        "[List equations reviewed with assessment]",
        "",
        "### Derivation Review",
        "[Assessment of derivations and proofs]",
        "",
        "### Notation Check",
        "[Consistency of notation]",
        "",
        "### Issues Found",
        "[List of potential errors or concerns]",
        "",
        "### Recommendations",
        "[Suggestions for improvement]",
        "```",
        "",
        "If no mathematical content is found, state that clearly and skip detailed analysis.",
    ])
    
    return Task(
        description="\n".join(prompt_parts),
        expected_output=(
            "A structured mathematical review with sections for equations, derivations, "
            "notation, issues found, and recommendations. If no math content, state that clearly."
        ),
        agent=agent,
    )


def detect_math_content(text: str) -> bool:
    """
    Detect if text contains significant mathematical content.
    
    Args:
        text: Paper text to check
    
    Returns:
        True if mathematical content is detected
    """
    import re
    
    math_indicators = [
        # LaTeX math environments
        r'\\begin\{equation',
        r'\\begin\{align',
        r'\\begin\{theorem',
        r'\\begin\{proof',
        r'\\begin\{lemma',
        r'\\begin\{proposition',
        r'\\begin\{corollary',
        r'\$\$.+?\$\$',  # Display math
        r'\$[^$]+\$',    # Inline math
        # Common math symbols (escaped for LaTeX)
        r'\\frac',
        r'\\sum',
        r'\\int',
        r'\\partial',
        r'\\nabla',
        r'\\alpha',
        r'\\beta',
        r'\\gamma',
        r'\\theta',
        r'\\lambda',
        r'\\sigma',
        # Equation references
        r'[Ee]quation\s*[\(\[]?\d+',
        r'[Ee]q\.\s*[\(\[]?\d+',
        # Math terms (case insensitive)
        r'\btheorem\b',
        r'\blemma\b',
        r'\bproof\b',
        r'\bcorollary\b',
        r'\bproposition\b',
        r'\bderivative\b',
        r'\bintegral\b',
        r'\bmatrix\b',
        r'\bvector\b',
        r'\beigenvalue\b',
        r'\bconvergence\b',
        r'\bdivergence\b',
        r'\boptimization\b',
        r'\bgradient\b',
        r'\bhessian\b',
        # Math operators
        r'argmax',
        r'argmin',
        r'∑|∫|∂|∇|α|β|γ|θ|λ|σ',  # Unicode math symbols
    ]
    
    math_count = 0
    for pattern in math_indicators:
        try:
            matches = re.findall(pattern, text, re.IGNORECASE)
            math_count += len(matches)
        except re.error:
            continue
    
    # Consider math-heavy if more than 5 math indicators found
    return math_count >= 5


def extract_math_content(text: str) -> str:
    """
    Extract mathematical content from paper text.
    
    Extracts equations, proofs, theorems, and surrounding context.
    
    Args:
        text: Full paper text
    
    Returns:
        Extracted mathematical content
    """
    import re
    
    extracted_parts = []
    
    # Extract LaTeX math environments
    math_env_patterns = [
        r'\\begin\{equation\}.*?\\end\{equation\}',
        r'\\begin\{align\*?\}.*?\\end\{align\*?\}',
        r'\\begin\{theorem\}.*?\\end\{theorem\}',
        r'\\begin\{proof\}.*?\\end\{proof\}',
        r'\\begin\{lemma\}.*?\\end\{lemma\}',
        r'\\begin\{proposition\}.*?\\end\{proposition\}',
        r'\\begin\{corollary\}.*?\\end\{corollary\}',
        r'\\begin\{definition\}.*?\\end\{definition\}',
        r'\$\$[^$]+\$\$',  # Display math
    ]
    
    for pattern in math_env_patterns:
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        extracted_parts.extend(matches)
    
    # Extract paragraphs containing math-heavy content
    paragraphs = text.split('\n\n')
    for para in paragraphs:
        # Check if paragraph has inline math or equation references
        if re.search(r'\$[^$]+\$|Eq\.|Equation|\\frac|\\sum|\\int', para):
            if para not in extracted_parts:
                extracted_parts.append(para)
    
    if not extracted_parts:
        return "No explicit mathematical content (equations, proofs) detected in the paper."
    
    # Combine and truncate to token limit
    combined = "\n\n---\n\n".join(extracted_parts)
    return combined[:20000]  # ~5k tokens max for math content
