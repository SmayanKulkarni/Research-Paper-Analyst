from functools import lru_cache
from typing import List

from sentence_transformers import SentenceTransformer

from app.config import get_settings

settings = get_settings()


@lru_cache
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(settings.EMBEDDING_MODEL_NAME)


def embed_texts(texts: List[str]) -> List[list]:
    model = get_embedding_model()
    vectors = model.encode(texts, convert_to_numpy=False)
    return [v.tolist() for v in vectors]
