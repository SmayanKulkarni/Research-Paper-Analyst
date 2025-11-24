from typing import Dict, List
from app.config import get_settings
from app.services.pdf_parser import parse_pdf_to_text_and_images

settings = get_settings()


def load_pdf(file_id: str) -> Dict[str, List[str]]:
    """
    Given a file_id (UUID name of stored PDF), load and parse it.
    """
    import os

    uploads_dir = os.path.join(settings.STORAGE_ROOT, settings.UPLOADS_DIR)
    file_path = os.path.join(uploads_dir, f"{file_id}.pdf")

    return parse_pdf_to_text_and_images(file_path)
