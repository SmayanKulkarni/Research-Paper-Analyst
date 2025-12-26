"""
Vision Tool for Scientific Image Analysis.

Uses Groq's vision model to analyze scientific figures, charts, and diagrams
from research papers.
"""

import base64
import os
from typing import List, Dict, Any
from crewai.tools import tool
from groq import Groq

from app.config import get_settings

settings = get_settings()


def _encode_image_to_base64(path: str) -> str:
    """Encode image file to base64 string."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _get_image_mime_type(path: str) -> str:
    """Get MIME type from file extension."""
    ext = os.path.splitext(path)[1].lower()
    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return mime_types.get(ext, "image/png")


def _get_groq_model_name(model: str) -> str:
    """Strip groq/ prefix for direct Groq SDK calls."""
    if model.startswith("groq/"):
        return model[5:]
    return model


def analyze_single_image(image_path: str, client: Groq, model: str) -> Dict[str, Any]:
    """
    Analyze a single image using Groq's vision model.
    
    Args:
        image_path: Path to the image file
        client: Groq client instance
        model: Model name to use
    
    Returns:
        Dictionary with analysis results
    """
    if not os.path.exists(image_path):
        return {"filename": os.path.basename(image_path), "error": "File not found"}
    
    try:
        base64_image = _encode_image_to_base64(image_path)
        mime_type = _get_image_mime_type(image_path)
        file_size = os.path.getsize(image_path)
        
        # Skip very small images (likely artifacts or noise)
        if file_size < 1000:  # < 1KB
            return {
                "filename": os.path.basename(image_path),
                "error": "Image too small (likely artifact or noise)",
            }
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Analyze this scientific figure from a research paper. "
                                "Describe:\n"
                                "1. What type of figure it is (chart, diagram, table, photo, etc.)\n"
                                "2. Key information/data it conveys\n"
                                "3. Quality assessment (clarity, labeling, legends)\n"
                                "4. Any issues or improvements needed\n"
                                "Be concise but thorough. If the image is blank or unclear, say so."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=settings.MAX_VISION_TOKENS,
            temperature=0.1,  # Lower temp for more consistent output
        )
        
        content = response.choices[0].message.content
        if not content or content.strip() == "":
            return {
                "filename": os.path.basename(image_path),
                "error": "LLM returned empty response (image may be invalid or unsafe)",
            }
        
        return {
            "filename": os.path.basename(image_path),
            "analysis": content,
            "tokens_used": response.usage.total_tokens if response.usage else 0,
        }
        
    except Exception as e:
        return {
            "filename": os.path.basename(image_path),
            "error": f"Vision analysis failed: {str(e)[:100]}",
        }


@tool("Analyze Scientific Images")
def vision_tool(image_paths: str) -> str:
    """
    Analyze scientific images from a research paper using vision AI.
    
    Input: Comma-separated list of image file paths
    Output: Detailed analysis of each image including type, content, quality, and suggestions.
    
    Use this tool when you need to analyze figures, charts, diagrams, or tables from a paper.
    """
    # Parse image paths (handle both list and comma-separated string)
    if isinstance(image_paths, str):
        paths = [p.strip() for p in image_paths.split(",") if p.strip()]
    else:
        paths = list(image_paths)
    
    if not paths:
        return "No image paths provided for analysis."
    
    # Initialize Groq client
    client = Groq(api_key=settings.GROQ_API_KEY)
    model = _get_groq_model_name(settings.GROQ_VISION_MODEL)
    
    results = []
    total_tokens = 0
    successful = 0
    
    for path in paths:
        result = analyze_single_image(path, client, model)
        results.append(result)
        if "analysis" in result and "error" not in result:
            successful += 1
        total_tokens += result.get("tokens_used", 0)
    
    # Format output
    output_parts = [f"## Vision Analysis Report\n\nAnalyzed {len(results)} images ({successful} successful).\n"]
    
    for i, result in enumerate(results, 1):
        output_parts.append(f"\n### Image {i}: {result['filename']}\n")
        
        if "error" in result:
            output_parts.append(f"**Status:** {result['error']}\n")
        elif "analysis" in result:
            output_parts.append(result["analysis"])
            output_parts.append("\n")
        else:
            output_parts.append("No analysis available.\n")
    
    output_parts.append(f"\n---\n*Total tokens used: {total_tokens}*")
    
    final_output = "\n".join(output_parts)
    if not final_output or final_output.strip() == "":
        return "Vision analysis could not be completed - all images failed or were invalid."
    return final_output


# Legacy function for backward compatibility
def encode_image(path: str) -> str:
    """Helper to encode image to base64 (legacy compatibility)."""
    return _encode_image_to_base64(path)
