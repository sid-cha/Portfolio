from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "RAG Knowledge Search Engine"
    DEBUG: bool = False
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "https://sid-cha.github.io"]

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536

    # Vector DB (ChromaDB local, or Pinecone for prod)
    VECTOR_DB: str = "chroma"          # "chroma" | "pinecone"
    CHROMA_PATH: str = "./data/chroma"
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX: str = "rag-engine"

    # PostgreSQL (document metadata)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/rag_engine"

    # Redis (response caching)
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_TTL: int = 3600  # 1 hour

    # Chunking
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64

    # Retrieval
    TOP_K_VECTOR: int = 10
    TOP_K_BM25: int = 10
    TOP_K_RERANK: int = 5
    HYBRID_ALPHA: float = 0.7  # Weight for vector vs BM25 (1.0 = pure vector)

    # Reranker
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
