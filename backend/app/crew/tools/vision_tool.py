import base64
import os
from crewai import Tool


def encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_images(image_paths: list[str]) -> dict:
    """
    Converts images to base64 so the vision model can analyze them.
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


vision_tool = Tool(
    name="vision_tool",
    description="Encodes images and sends them for vision analysis.",
    func=analyze_images
)
