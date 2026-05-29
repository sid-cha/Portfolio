"""
Search API
POST /api/v1/search        — standard search (JSON response)
POST /api/v1/search/stream — streaming search (SSE)
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.retriever import retrieve
from app.services.generator import generate_answer, build_citations

router = APIRouter()
logger = logging.getLogger(__name__)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: Optional[int] = Field(5, ge=1, le=20)
    stream: Optional[bool] = False


class Citation(BaseModel):
    index: int
    source: str
    page: Optional[int]
    source_type: str
    score: float
    preview: str


class SearchResponse(BaseModel):
    query: str
    answer: str
    citations: list[Citation]
    chunks_retrieved: int


@router.post("", response_model=SearchResponse)
async def search(req: SearchRequest):
    """Full RAG search: retrieve → rerank → generate with citations."""
    chunks = retrieve(req.query, top_k=req.top_k)
    if not chunks:
        return SearchResponse(
            query=req.query,
            answer="No relevant documents found. Please ingest documents first.",
            citations=[],
            chunks_retrieved=0,
        )

    answer_parts = []
    async for token in generate_answer(req.query, chunks, stream=False):
        answer_parts.append(token)

    return SearchResponse(
        query=req.query,
        answer="".join(answer_parts),
        citations=[Citation(**c) for c in build_citations(chunks)],
        chunks_retrieved=len(chunks),
    )


@router.post("/stream")
async def search_stream(req: SearchRequest):
    """
    Streaming RAG search via Server-Sent Events.
    First event: citations JSON.
    Subsequent events: streamed answer tokens.
    Final event: [DONE].
    """
    async def event_generator():
        try:
            chunks = retrieve(req.query, top_k=req.top_k)

            # Emit citations first
            citations = build_citations(chunks)
            yield f"event: citations\ndata: {json.dumps(citations)}\n\n"

            if not chunks:
                yield "data: No relevant documents found.\n\ndata: [DONE]\n\n"
                return

            # Stream answer tokens
            async for token in generate_answer(req.query, chunks, stream=True):
                yield token

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: Error: {str(e)}\n\ndata: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
