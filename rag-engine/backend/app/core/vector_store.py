"""
Vector store abstraction — supports ChromaDB (local dev) and Pinecone (production).
"""

import logging
from functools import lru_cache
from typing import List, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)

_vector_store = None


def get_vector_store():
    global _vector_store
    if _vector_store is None:
        if settings.VECTOR_DB == "chroma":
            _vector_store = ChromaVectorStore()
        elif settings.VECTOR_DB == "pinecone":
            _vector_store = PineconeVectorStore()
        else:
            raise ValueError(f"Unknown VECTOR_DB: {settings.VECTOR_DB}")
        logger.info(f"Initialized vector store: {settings.VECTOR_DB}")
    return _vector_store


class ChromaVectorStore:
    def __init__(self):
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PATH,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(self, ids: List[str], embeddings: List[List[float]],
               documents: List[str], metadatas: List[dict]):
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def query(self, embedding: List[float], top_k: int) -> List[Tuple[str, float, dict]]:
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        items = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            score = 1 - dist  # cosine distance → similarity
            items.append((doc, score, meta))
        return items

    def delete_by_source(self, source: str):
        results = self.collection.get(where={"source": source})
        if results["ids"]:
            self.collection.delete(ids=results["ids"])


class PineconeVectorStore:
    def __init__(self):
        from pinecone import Pinecone
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index = pc.Index(settings.PINECONE_INDEX)

    def upsert(self, ids: List[str], embeddings: List[List[float]],
               documents: List[str], metadatas: List[dict]):
        vectors = [
            {"id": id_, "values": emb, "metadata": {**meta, "text": doc}}
            for id_, emb, doc, meta in zip(ids, embeddings, documents, metadatas)
        ]
        self.index.upsert(vectors=vectors)

    def query(self, embedding: List[float], top_k: int) -> List[Tuple[str, float, dict]]:
        results = self.index.query(vector=embedding, top_k=top_k, include_metadata=True)
        return [
            (match.metadata.get("text", ""), match.score, match.metadata)
            for match in results.matches
        ]

    def delete_by_source(self, source: str):
        self.index.delete(filter={"source": {"$eq": source}})
