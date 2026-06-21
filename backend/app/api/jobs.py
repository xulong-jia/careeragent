from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse, ListResponse
from app.schemas.jobs import JobCreateRequest, JobRecord
from app.services.job_service import (
    create_job as create_job_record,
    get_job as get_job_record,
    list_jobs,
)


router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=ApiResponse[JobRecord], status_code=status.HTTP_201_CREATED)
async def create_job(
    request: Request, payload: JobCreateRequest, db: Session = Depends(get_db)
) -> dict[str, object]:
    job = create_job_record(db, payload)
    return {"data": job, "request_id": request.state.request_id}


@router.get("", response_model=ApiResponse[ListResponse[JobRecord]])
async def list_job_records(
    request: Request, db: Session = Depends(get_db)
) -> dict[str, object]:
    items = list_jobs(db)
    return {
        "data": ListResponse(items=items, total=len(items)),
        "request_id": request.state.request_id,
    }


@router.get("/{jd_id}", response_model=ApiResponse[JobRecord])
async def get_job_detail(
    request: Request, jd_id: str, db: Session = Depends(get_db)
) -> dict[str, object]:
    job = get_job_record(db, jd_id)
    return {"data": job, "request_id": request.state.request_id}
