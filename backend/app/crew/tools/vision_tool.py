import base64
import os
from typing import List, Dict, Any
from crewai.tools import tool

def encode_image(path: str) -> str:
    """Helper to encode image to base64."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

@tool("Scientific Vision Tool")
def vision_tool(image_paths: List[str]) -> Dict[str, Any]:
    """
    Encodes images from the given paths into base64 format for vision analysis.
    Returns a dictionary containing the encoded images and analysis instructions.
    """
    encoded = []

    for p in image_paths:
        if os.path.exists(p):
            encoded.append({
                "filename": os.path.basename(p),
                "base64": encode_image(p)
            })

    return {
        "images": encoded,
        "instruction": (
            "Analyze the scientific image. Describe charts, structure, text, "
            "labels, clarity, and scientific meaning."
        )
    }