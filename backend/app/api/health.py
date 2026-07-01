from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import get_settings, settings_summary, validate_runtime_settings


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


class ReadinessData(BaseModel):
    status: str
    database_reachable: bool
    config_valid: bool
    config: dict[str, object]
    errors: list[str]


class ReadinessResponse(BaseModel):
    data: ReadinessData
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


@router.get("/ready", response_model=ReadinessResponse)
@router.get("/api/ready", response_model=ReadinessResponse)
async def get_readiness(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    settings = get_settings()
    errors: list[str] = []
    config_valid = True
    try:
        validate_runtime_settings(settings)
    except RuntimeError as exc:
        config_valid = False
        errors.append(str(exc))

    database_reachable = False
    try:
        db.execute(text("SELECT 1"))
        database_reachable = True
    except Exception:
        errors.append("Database is not reachable.")

    return {
        "data": {
            "status": "ok" if config_valid and database_reachable else "not_ready",
            "database_reachable": database_reachable,
            "config_valid": config_valid,
            "config": settings_summary(settings),
            "errors": errors,
        },
        "request_id": request.state.request_id,
    }
