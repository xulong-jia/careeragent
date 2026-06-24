from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse, ListResponse
from app.schemas.projects import (
    ProjectCreateRequest,
    ProjectRecord,
    ProjectStatus,
    ProjectUpdateRequest,
)
from app.services import project_service


router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post(
    "",
    response_model=ApiResponse[ProjectRecord],
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    request: Request,
    payload: ProjectCreateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    project = project_service.create_project(db, payload)
    return {"data": project, "request_id": request.state.request_id}


@router.get("", response_model=ApiResponse[ListResponse[ProjectRecord]])
async def list_projects(
    request: Request,
    profile_id: str | None = None,
    resume_version_id: str | None = None,
    status: ProjectStatus | None = None,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    items = project_service.list_projects(
        db,
        profile_id=profile_id,
        resume_version_id=resume_version_id,
        status=status,
    )
    return {
        "data": ListResponse(items=items, total=len(items)),
        "request_id": request.state.request_id,
    }


@router.get("/{project_id}", response_model=ApiResponse[ProjectRecord])
async def get_project(
    request: Request,
    project_id: str,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    project = project_service.get_project(db, project_id)
    return {"data": project, "request_id": request.state.request_id}


@router.patch("/{project_id}", response_model=ApiResponse[ProjectRecord])
async def update_project(
    request: Request,
    project_id: str,
    payload: ProjectUpdateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    project = project_service.update_project(db, project_id, payload)
    return {"data": project, "request_id": request.state.request_id}
