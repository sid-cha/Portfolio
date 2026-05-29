"""
LLM Generation Service
- Streaming responses via SSE
- Context injection with citation markers
- Source attribution in every response
"""

import logging
from typing import List, AsyncGenerator

from openai import AsyncOpenAI

from app.core.config import settings
from app.services.retriever import RetrievedChunk

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

SYSTEM_PROMPT = """You are an intelligent enterprise knowledge search assistant.
Answer the user's question using ONLY the provided context chunks below.
Each context chunk has a [Source N] label — cite sources inline like [Source 1] when using their content.
If the context does not contain sufficient information, say so honestly.
Be concise, accurate, and always cite your sources.
"""


def _build_context(chunks: List[RetrievedChunk]) -> str:
    parts = []
    for i, chunk in enumerate(chunks):
        source_label = f"{chunk.source}"
        if chunk.page:
            source_label += f" (page {chunk.page})"
        parts.append(f"[Source {i + 1}] ({source_label})\n{chunk.text}")
    return "\n\n---\n\n".join(parts)


async def generate_answer(
    query: str,
    chunks: List[RetrievedChunk],
    stream: bool = True,
) -> AsyncGenerator[str, None]:
    """
    Generate a cited answer from retrieved chunks.
    Yields SSE-formatted tokens when stream=True.
    """
    context = _build_context(chunks)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
    ]

    if stream:
        async for token in _stream_response(messages):
            yield token
    else:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            temperature=0.1,
        )
        yield response.choices[0].message.content


async def _stream_response(messages: list) -> AsyncGenerator[str, None]:
    stream = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        temperature=0.1,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield f"data: {delta}\n\n"
    yield "data: [DONE]\n\n"


def build_citations(chunks: List[RetrievedChunk]) -> List[dict]:
    """Build structured citation objects to return alongside the answer."""
    return [
        {
            "index": i + 1,
            "source": chunk.source,
            "page": chunk.page,
            "source_type": chunk.source_type,
            "score": round(chunk.score, 4),
            "preview": chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
        }
        for i, chunk in enumerate(chunks)
    ]
