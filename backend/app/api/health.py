from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.core.config import get_settings


router = APIRouter(tags=["health"])


class HealthData(BaseModel):
    status: str
    service: str
    environment: str


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
        },
        "request_id": request.state.request_id,
    }
