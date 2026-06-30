from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.core.config import get_settings


router = APIRouter(tags=["health"])


class HealthData(BaseModel):
    status: str
    service: str
    environment: str
    ai_provider_mode: str
    llm_provider: str
    embedding_provider: str
    vector_store: str
    rag_retrieval_mode: str
    real_llm_enabled: bool
    real_embedding_enabled: bool


class HealthResponse(BaseModel):
    data: HealthData
    request_id: str


@router.get("/health", response_model=HealthResponse)
async def get_health(request: Request) -> dict[str, object]:
    settings = get_settings()
    return {
        "data": {
            "status": "ok",
            "service": settings.app_name,
            "environment": settings.app_env,
            "ai_provider_mode": settings.ai_provider_mode,
            "llm_provider": settings.llm_provider,
            "embedding_provider": settings.embedding_provider,
            "vector_store": settings.vector_store,
            "rag_retrieval_mode": settings.rag_retrieval_mode,
            "real_llm_enabled": settings.enable_real_llm,
            "real_embedding_enabled": settings.enable_real_embedding,
        },
        "request_id": request.state.request_id,
    }
