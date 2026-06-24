from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse, ListResponse
from app.schemas.profiles import (
    ProfileCreateRequest,
    ProfileRecord,
    ProfileSummary,
    ProfileUpdateRequest,
)
from app.services import profile_service


router = APIRouter(prefix="/api/profiles", tags=["profiles"])


@router.post(
    "",
    response_model=ApiResponse[ProfileRecord],
    status_code=status.HTTP_201_CREATED,
)
async def create_profile(
    request: Request,
    payload: ProfileCreateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    profile = profile_service.create_profile(db, payload)
    return {"data": profile, "request_id": request.state.request_id}


@router.get("", response_model=ApiResponse[ListResponse[ProfileRecord]])
async def list_profiles(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    items = profile_service.list_profiles(db)
    return {
        "data": ListResponse(items=items, total=len(items)),
        "request_id": request.state.request_id,
    }


@router.get("/{profile_id}", response_model=ApiResponse[ProfileRecord])
async def get_profile(
    request: Request,
    profile_id: str,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    profile = profile_service.get_profile(db, profile_id)
    return {"data": profile, "request_id": request.state.request_id}


@router.patch("/{profile_id}", response_model=ApiResponse[ProfileRecord])
async def update_profile(
    request: Request,
    profile_id: str,
    payload: ProfileUpdateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    profile = profile_service.update_profile(db, profile_id, payload)
    return {"data": profile, "request_id": request.state.request_id}


@router.get("/{profile_id}/summary", response_model=ApiResponse[ProfileSummary])
async def get_profile_summary(
    request: Request,
    profile_id: str,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    summary = profile_service.summarize_profile(db, profile_id)
    return {"data": summary, "request_id": request.state.request_id}
