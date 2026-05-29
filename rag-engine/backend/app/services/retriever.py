"""
Retrieval Service
- Hybrid retrieval: vector (cosine) + BM25 keyword with Reciprocal Rank Fusion
- Cross-encoder re-ranking
- Source citation building
"""

import logging
from typing import List, Tuple
from dataclasses import dataclass

from app.core.config import settings
from app.core.vector_store import get_vector_store
from app.services.embedder import get_single_embedding
from app.services.bm25_search import bm25_search

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    text: str
    score: float
    source: str
    page: int | None
    chunk_index: int
    source_type: str  # "pdf" | "confluence" | "slack" | "text"


def retrieve(query: str, top_k: int = None) -> List[RetrievedChunk]:
    """
    Full hybrid retrieval pipeline:
    1. Embed query
    2. Vector search (ChromaDB / Pinecone)
    3. BM25 keyword search
    4. Reciprocal Rank Fusion merge
    5. Cross-encoder re-ranking
    """
    top_k = top_k or settings.TOP_K_RERANK

    # 1. Embed query
    query_embedding = get_single_embedding(query)

    # 2. Vector search
    vector_results = get_vector_store().query(query_embedding, settings.TOP_K_VECTOR)

    # 3. BM25 search
    bm25_results = bm25_search(query, settings.TOP_K_BM25)

    # 4. Reciprocal Rank Fusion
    fused = _reciprocal_rank_fusion(vector_results, bm25_results, alpha=settings.HYBRID_ALPHA)

    # 5. Cross-encoder re-ranking
    reranked = _rerank(query, fused, top_k)

    logger.info(f"Retrieved {len(reranked)} chunks for query: '{query[:60]}...'")
    return reranked


def _reciprocal_rank_fusion(
    vector_results: List[Tuple[str, float, dict]],
    bm25_results: List[Tuple[str, float, dict]],
    alpha: float = 0.7,
    k: int = 60,
) -> List[Tuple[str, float, dict]]:
    """
    Merge vector and BM25 results using Reciprocal Rank Fusion.
    alpha controls weight: 1.0 = pure vector, 0.0 = pure BM25.
    """
    scores: dict[str, float] = {}
    meta_map: dict[str, dict] = {}

    for rank, (text, _, meta) in enumerate(vector_results):
        doc_id = meta.get("chunk_id", text[:64])
        scores[doc_id] = scores.get(doc_id, 0) + alpha * (1 / (k + rank + 1))
        meta_map[doc_id] = (text, meta)

    for rank, (text, _, meta) in enumerate(bm25_results):
        doc_id = meta.get("chunk_id", text[:64])
        scores[doc_id] = scores.get(doc_id, 0) + (1 - alpha) * (1 / (k + rank + 1))
        meta_map.setdefault(doc_id, (text, meta))

    sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)
    return [(meta_map[id_][0], scores[id_], meta_map[id_][1]) for id_ in sorted_ids]


def _rerank(
    query: str,
    candidates: List[Tuple[str, float, dict]],
    top_k: int,
) -> List[RetrievedChunk]:
    """
    Cross-encoder re-ranking using ms-marco-MiniLM.
    Falls back to RRF scores if model unavailable.
    """
    if not candidates:
        return []

    try:
        from sentence_transformers import CrossEncoder
        model = CrossEncoder(settings.RERANKER_MODEL)
        pairs = [(query, text) for text, _, _ in candidates]
        scores = model.predict(pairs)
        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        top = ranked[:top_k]
    except Exception as e:
        logger.warning(f"Cross-encoder failed, using RRF scores: {e}")
        top = [(c, c[1]) for c in candidates[:top_k]]

    results = []
    for (text, _, meta), score in top:
        results.append(RetrievedChunk(
            text=text,
            score=float(score),
            source=meta.get("source", "Unknown"),
            page=meta.get("page"),
            chunk_index=meta.get("chunk_index", 0),
            source_type=meta.get("source_type", "text"),
        ))
    return results
