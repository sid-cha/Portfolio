"""
Chunking Service
Strategies: recursive character splitting, token-aware (tiktoken), semantic (sentence boundaries)
"""

import re
import logging
from typing import List
from dataclasses import dataclass

import tiktoken

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    text: str
    chunk_index: int
    strategy: str
    token_count: int
    char_count: int


def chunk_document(text: str, strategy: str = "recursive") -> List[Chunk]:
    """
    Split a document into chunks using the specified strategy.

    Args:
        text: Full document text
        strategy: "recursive" | "token" | "semantic"

    Returns:
        List of Chunk objects
    """
    text = _clean_text(text)

    if strategy == "token":
        raw_chunks = _token_aware_split(text)
    elif strategy == "semantic":
        raw_chunks = _semantic_split(text)
    else:
        raw_chunks = _recursive_split(text)

    enc = tiktoken.get_encoding("cl100k_base")
    chunks = []
    for i, chunk_text in enumerate(raw_chunks):
        if len(chunk_text.strip()) < 30:
            continue  # skip tiny fragments
        chunks.append(Chunk(
            text=chunk_text.strip(),
            chunk_index=i,
            strategy=strategy,
            token_count=len(enc.encode(chunk_text)),
            char_count=len(chunk_text),
        ))

    logger.info(f"Chunked document into {len(chunks)} chunks (strategy={strategy})")
    return chunks


# ── RECURSIVE CHARACTER SPLITTING ──────────────────────────────────────────────

def _recursive_split(text: str, size: int = None, overlap: int = None) -> List[str]:
    size = size or settings.CHUNK_SIZE * 4   # approximate chars from tokens
    overlap = overlap or settings.CHUNK_OVERLAP * 4

    separators = ["\n\n", "\n", ". ", "! ", "? ", ", ", " ", ""]
    return _recursive_split_by_sep(text, separators, size, overlap)


def _recursive_split_by_sep(text: str, separators: List[str],
                              size: int, overlap: int) -> List[str]:
    if len(text) <= size:
        return [text]

    sep = ""
    for s in separators:
        if s in text:
            sep = s
            break

    parts = text.split(sep) if sep else list(text)
    chunks, current = [], ""

    for part in parts:
        piece = (current + sep + part) if current else part
        if len(piece) <= size:
            current = piece
        else:
            if current:
                chunks.append(current)
            if len(part) > size:
                chunks.extend(_recursive_split_by_sep(part, separators[1:], size, overlap))
                current = ""
            else:
                current = part

    if current:
        chunks.append(current)

    # Apply overlap
    if overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            tail = chunks[i - 1][-overlap:]
            overlapped.append(tail + chunks[i])
        return overlapped

    return chunks


# ── TOKEN-AWARE SPLITTING ───────────────────────────────────────────────────────

def _token_aware_split(text: str) -> List[str]:
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    size = settings.CHUNK_SIZE
    overlap = settings.CHUNK_OVERLAP
    chunks = []

    start = 0
    while start < len(tokens):
        end = min(start + size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunks.append(enc.decode(chunk_tokens))
        start += size - overlap

    return chunks


# ── SEMANTIC SPLITTING (sentence-boundary aware) ────────────────────────────────

def _semantic_split(text: str) -> List[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text)
    enc = tiktoken.get_encoding("cl100k_base")
    size = settings.CHUNK_SIZE

    chunks, current_tokens, current_sents = [], 0, []

    for sentence in sentences:
        sent_tokens = len(enc.encode(sentence))
        if current_tokens + sent_tokens > size and current_sents:
            chunks.append(" ".join(current_sents))
            # Overlap: keep last sentence
            current_sents = current_sents[-1:]
            current_tokens = len(enc.encode(current_sents[0])) if current_sents else 0
        current_sents.append(sentence)
        current_tokens += sent_tokens

    if current_sents:
        chunks.append(" ".join(current_sents))

    return chunks


# ── UTILITIES ───────────────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    text = re.sub(r'\x00', '', text)           # null bytes
    text = re.sub(r'\r\n', '\n', text)          # normalize newlines
    text = re.sub(r'\n{3,}', '\n\n', text)      # collapse excessive blank lines
    text = re.sub(r'[ \t]{2,}', ' ', text)      # collapse spaces
    return text.strip()
