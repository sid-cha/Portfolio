"""
Embeddings Service
Supports OpenAI text-embedding-3-small and local sentence-transformers.
"""

import logging
from typing import List

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_embeddings(texts: List[str], model: str = None) -> List[List[float]]:
    model = model or settings.EMBEDDING_MODEL
    if model.startswith("text-embedding"):
        return _openai_embeddings(texts, model)
    else:
        return _sentence_transformer_embeddings(texts, model)


def get_single_embedding(text: str, model: str = None) -> List[float]:
    return get_embeddings([text], model)[0]


def _openai_embeddings(texts: List[str], model: str) -> List[List[float]]:
    from openai import OpenAI
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # Batch in groups of 100 (OpenAI limit)
    all_embeddings = []
    for i in range(0, len(texts), 100):
        batch = texts[i:i + 100]
        response = client.embeddings.create(model=model, input=batch)
        all_embeddings.extend([item.embedding for item in response.data])

    logger.info(f"Generated {len(all_embeddings)} embeddings via OpenAI ({model})")
    return all_embeddings


def _sentence_transformer_embeddings(texts: List[str], model: str) -> List[List[float]]:
    from sentence_transformers import SentenceTransformer
    st_model = SentenceTransformer(model)
    embeddings = st_model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    logger.info(f"Generated {len(embeddings)} embeddings via SentenceTransformer ({model})")
    return embeddings.tolist()
