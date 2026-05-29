"""
BM25 Keyword Search Service
Used for hybrid retrieval alongside vector search.
"""

import logging
import pickle
from pathlib import Path
from typing import List, Tuple

from rank_bm25 import BM25Okapi

from app.core.config import settings

logger = logging.getLogger(__name__)

BM25_INDEX_PATH = Path("./data/bm25_index.pkl")
_bm25_index: BM25Okapi | None = None
_bm25_corpus: List[dict] | None = None  # [{id, text, metadata}]


def _tokenize(text: str) -> List[str]:
    return text.lower().split()


def build_bm25_index(documents: List[dict]):
    """
    Build or rebuild the BM25 index from a list of {id, text, metadata} dicts.
    """
    global _bm25_index, _bm25_corpus
    _bm25_corpus = documents
    tokenized = [_tokenize(doc["text"]) for doc in documents]
    _bm25_index = BM25Okapi(tokenized)

    BM25_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BM25_INDEX_PATH, "wb") as f:
        pickle.dump((_bm25_index, _bm25_corpus), f)
    logger.info(f"BM25 index built with {len(documents)} documents")


def load_bm25_index():
    global _bm25_index, _bm25_corpus
    if BM25_INDEX_PATH.exists():
        with open(BM25_INDEX_PATH, "rb") as f:
            _bm25_index, _bm25_corpus = pickle.load(f)
        logger.info(f"BM25 index loaded ({len(_bm25_corpus)} documents)")


def bm25_search(query: str, top_k: int = 10) -> List[Tuple[str, float, dict]]:
    """
    Returns list of (text, score, metadata) tuples.
    """
    if _bm25_index is None:
        load_bm25_index()
    if _bm25_index is None or not _bm25_corpus:
        return []

    tokenized_query = _tokenize(query)
    scores = _bm25_index.get_scores(tokenized_query)

    indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
    results = []
    for idx, score in indexed:
        if score > 0:
            doc = _bm25_corpus[idx]
            results.append((doc["text"], float(score), doc["metadata"]))

    return results
