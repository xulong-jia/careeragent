from fastapi import APIRouter, Depends, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse, ListResponse
from app.schemas.resumes import ResumeRecord, ResumeVersionRecord
from app.services.resume_service import (
    create_resume,
    get_resume as get_resume_record,
    list_resume_versions,
    list_resumes,
)


router = APIRouter(prefix="/api/resumes", tags=["resumes"])


@router.post(
    "/upload",
    response_model=ApiResponse[ResumeRecord],
    status_code=status.HTTP_201_CREATED,
)
async def upload_resume(
    request: Request, file: UploadFile, db: Session = Depends(get_db)
) -> dict[str, object]:
    content = await file.read()
    resume = create_resume(db, file.filename or "", file.content_type, content)
    return {"data": resume, "request_id": request.state.request_id}


@router.get("", response_model=ApiResponse[ListResponse[ResumeRecord]])
async def list_resume_records(
    request: Request, db: Session = Depends(get_db)
) -> dict[str, object]:
    items = list_resumes(db)
    return {
        "data": ListResponse(items=items, total=len(items)),
        "request_id": request.state.request_id,
    }


@router.get("/{resume_id}", response_model=ApiResponse[ResumeRecord])
async def get_resume_detail(
    request: Request, resume_id: str, db: Session = Depends(get_db)
) -> dict[str, object]:
    resume = get_resume_record(db, resume_id)
    return {"data": resume, "request_id": request.state.request_id}


@router.get(
    "/{resume_id}/versions",
    response_model=ApiResponse[ListResponse[ResumeVersionRecord]],
)
async def list_resume_version_records(
    request: Request, resume_id: str, db: Session = Depends(get_db)
) -> dict[str, object]:
    items = list_resume_versions(db, resume_id)
    return {
        "data": ListResponse(items=items, total=len(items)),
        "request_id": request.state.request_id,
    }
