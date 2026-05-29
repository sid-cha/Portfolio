"""
Ingest API
POST /api/v1/ingest/upload  — upload a document file
POST /api/v1/ingest/url     — ingest from URL
DELETE /api/v1/ingest/{source} — remove a source
"""

import uuid
import logging
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from pydantic import BaseModel

from app.services.parser import parse_document
from app.services.chunker import chunk_document
from app.services.embedder import get_embeddings
from app.services.bm25_search import build_bm25_index, _bm25_corpus
from app.core.vector_store import get_vector_store

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("./data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class IngestResponse(BaseModel):
    source: str
    chunks_created: int
    message: str


@router.post("/upload", response_model=IngestResponse)
async def ingest_upload(
    file: UploadFile = File(...),
    chunk_strategy: str = Form("recursive"),
):
    """Upload and ingest a document (PDF, TXT, MD, HTML, JSON)."""
    allowed = {".pdf", ".txt", ".md", ".html", ".json"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, f"File type {ext} not supported. Allowed: {allowed}")

    # Save upload
    save_path = UPLOAD_DIR / f"{uuid.uuid4()}{ext}"
    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    return await _ingest_file(str(save_path), file.filename, chunk_strategy)


@router.post("/url", response_model=IngestResponse)
async def ingest_url(url: str, chunk_strategy: str = "recursive"):
    """Fetch and ingest a web page."""
    import httpx
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    save_path = UPLOAD_DIR / f"{uuid.uuid4()}.html"
    with open(save_path, "wb") as f:
        f.write(resp.content)

    return await _ingest_file(str(save_path), url, chunk_strategy)


@router.delete("/{source}")
async def delete_source(source: str):
    """Remove all chunks for a given source from the vector store."""
    get_vector_store().delete_by_source(source)
    return {"message": f"Deleted all chunks for source: {source}"}


async def _ingest_file(file_path: str, source_name: str, strategy: str) -> IngestResponse:
    try:
        # 1. Parse
        text, source_type = parse_document(file_path)

        # 2. Chunk
        chunks = chunk_document(text, strategy=strategy)
        if not chunks:
            raise HTTPException(400, "No content extracted from document")

        # 3. Embed
        texts = [c.text for c in chunks]
        embeddings = get_embeddings(texts)

        # 4. Build metadata
        ids, metadatas = [], []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{source_name}_{i}"
            ids.append(chunk_id)
            metadatas.append({
                "chunk_id": chunk_id,
                "source": source_name,
                "source_type": source_type,
                "chunk_index": chunk.chunk_index,
                "token_count": chunk.token_count,
                "strategy": chunk.strategy,
            })

        # 5. Upsert into vector store
        get_vector_store().upsert(ids, embeddings, texts, metadatas)

        # 6. Update BM25 index
        corpus = (_bm25_corpus or []) + [
            {"id": ids[i], "text": texts[i], "metadata": metadatas[i]}
            for i in range(len(chunks))
        ]
        build_bm25_index(corpus)

        logger.info(f"Ingested '{source_name}': {len(chunks)} chunks")
        return IngestResponse(
            source=source_name,
            chunks_created=len(chunks),
            message=f"Successfully ingested {len(chunks)} chunks from '{source_name}'",
        )

    except Exception as e:
        logger.error(f"Ingest failed for {source_name}: {e}")
        raise HTTPException(500, f"Ingest failed: {str(e)}")
