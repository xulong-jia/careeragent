from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.applications import (
    ApplicationCreateRequest,
    ApplicationRecord,
    ApplicationStats,
    ApplicationUpdateRequest,
)
from app.schemas.common import ApiResponse, ListResponse
from app.services import application_service


router = APIRouter(prefix="/api/applications", tags=["applications"])


@router.post(
    "",
    response_model=ApiResponse[ApplicationRecord],
    status_code=status.HTTP_201_CREATED,
)
async def create_application(
    request: Request,
    payload: ApplicationCreateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    application = application_service.create_application(db, payload)
    return {"data": application, "request_id": request.state.request_id}


@router.get("", response_model=ApiResponse[ListResponse[ApplicationRecord]])
async def list_applications(
    request: Request,
    status: str | None = Query(default=None),
    company: str | None = Query(default=None),
    role_category: str | None = Query(default=None),
    resume_version_id: str | None = Query(default=None),
    jd_id: str | None = Query(default=None),
    agent_run_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    items = application_service.list_applications(
        db,
        status=status,
        company=company,
        role_category=role_category,
        resume_version_id=resume_version_id,
        jd_id=jd_id,
        agent_run_id=agent_run_id,
    )
    return {
        "data": ListResponse(items=items, total=len(items)),
        "request_id": request.state.request_id,
    }


@router.get("/stats", response_model=ApiResponse[ApplicationStats])
async def get_application_stats(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    stats = application_service.get_application_stats(db)
    return {"data": stats, "request_id": request.state.request_id}


@router.get("/{application_id}", response_model=ApiResponse[ApplicationRecord])
async def get_application(
    request: Request,
    application_id: str,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    application = application_service.get_application(db, application_id)
    return {"data": application, "request_id": request.state.request_id}


@router.patch("/{application_id}", response_model=ApiResponse[ApplicationRecord])
async def update_application(
    request: Request,
    application_id: str,
    payload: ApplicationUpdateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    application = application_service.update_application(db, application_id, payload)
    return {"data": application, "request_id": request.state.request_id}
