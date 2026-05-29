from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()

@router.get("/health")
async def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "vector_db": settings.VECTOR_DB,
        "embedding_model": settings.EMBEDDING_MODEL,
        "llm_model": settings.OPENAI_MODEL,
    }
