from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.resumes import ResumeVersionCloneRequest, ResumeVersionRecord
from app.services.resume_service import (
    archive_resume_version,
    clone_resume_version,
    get_resume_version,
)


router = APIRouter(prefix="/api/resume-versions", tags=["resume-versions"])


@router.get("/{version_id}", response_model=ApiResponse[ResumeVersionRecord])
def get_resume_version_detail(
    request: Request, version_id: str, db: Session = Depends(get_db)
) -> dict[str, object]:
    version = get_resume_version(db, version_id)
    return {"data": version, "request_id": request.state.request_id}


@router.post(
    "/{version_id}/clone",
    response_model=ApiResponse[ResumeVersionRecord],
    status_code=status.HTTP_201_CREATED,
)
def clone_resume_version_record(
    request: Request,
    version_id: str,
    payload: ResumeVersionCloneRequest | None = None,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    version = clone_resume_version(db, version_id, payload or ResumeVersionCloneRequest())
    return {"data": version, "request_id": request.state.request_id}


@router.patch("/{version_id}/archive", response_model=ApiResponse[ResumeVersionRecord])
def archive_resume_version_record(
    request: Request, version_id: str, db: Session = Depends(get_db)
) -> dict[str, object]:
    version = archive_resume_version(db, version_id)
    return {"data": version, "request_id": request.state.request_id}
