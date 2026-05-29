# RAG-Powered Enterprise Knowledge Search Engine

> Built by [Siddharth Chauhan](https://linkedin.com/in/sid-cha/) · [Portfolio](https://sid-cha.github.io)

A production-grade Retrieval-Augmented Generation system enabling semantic search over enterprise documents with hybrid retrieval, cross-encoder re-ranking, and real-time cited responses.

## Architecture

```
Documents (PDF/Confluence/Slack)
        ↓
   [Parser]  ← PyMuPDF, unstructured
        ↓
   [Chunker] ← recursive / token / semantic
        ↓
  [Embedder] ← text-embedding-3-small
        ↓
 [Vector DB] ← ChromaDB (dev) / Pinecone (prod)
        ↓
[BM25 Index] ← rank-bm25 (keyword search)
        ↓  ↑
 Query ────→ [Hybrid RRF Retrieval]
                    ↓
           [Cross-Encoder Rerank]
                    ↓
          [GPT-4o Generation + SSE]
                    ↓
          Cited Answer → Frontend
```

## Quick Start

```bash
# 1. Clone
git clone https://github.com/sid-cha/rag-engine.git
cd rag-engine

# 2. Configure
cp backend/.env.example backend/.env
# Edit backend/.env → add OPENAI_API_KEY

# 3. Run full stack
docker-compose up --build

# Frontend → http://localhost:3000
# API docs → http://localhost:8000/docs
```

## Local Dev (no Docker)

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your OPENAI_API_KEY
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/health` | GET | Health check |
| `/api/v1/ingest/upload` | POST | Upload & ingest a file |
| `/api/v1/ingest/url` | POST | Ingest from a URL |
| `/api/v1/search` | POST | Semantic search (JSON) |
| `/api/v1/search/stream` | POST | Streaming search (SSE) |

### Search Example

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "How does our authentication work?", "top_k": 5}'
```

```json
{
  "query": "How does our authentication work?",
  "answer": "Authentication uses JWT tokens [Source 1] with a 24-hour expiry...",
  "citations": [
    {"index": 1, "source": "auth-docs.pdf", "page": 3, "score": 0.94, "preview": "..."}
  ],
  "chunks_retrieved": 5
}
```

## Key Concepts

- **Hybrid Retrieval**: Reciprocal Rank Fusion merges vector (cosine similarity) and BM25 keyword results
- **Chunking Strategies**: Recursive character splitting, token-aware (tiktoken), semantic (sentence-boundary)
- **Cross-Encoder Re-ranking**: `ms-marco-MiniLM-L-6-v2` rescores top candidates for precision
- **Streaming**: Server-Sent Events deliver tokens as they're generated
- **Citations**: Every answer includes `[Source N]` inline markers with source metadata

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, LangChain |
| LLM | OpenAI GPT-4o / Ollama Llama 3 |
| Embeddings | text-embedding-3-small |
| Vector DB | ChromaDB (dev), Pinecone (prod) |
| Keyword Search | BM25 (rank-bm25) |
| Re-ranking | sentence-transformers cross-encoder |
| Frontend | React 18, TypeScript, Tailwind CSS |
| Infrastructure | Docker, Redis, PostgreSQL |

## Resume Bullet

> Built a RAG-based enterprise knowledge search engine using LangChain, FastAPI, and ChromaDB, enabling semantic search over 10K+ documents with hybrid retrieval (vector + BM25), cross-encoder re-ranking, and real-time cited responses — reducing information retrieval time by 80%.

---

**Author**: Siddharth Chauhan · [LinkedIn](https://linkedin.com/in/sid-cha/) · [GitHub](https://github.com/sid-cha)
