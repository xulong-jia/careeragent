from fastapi import APIRouter, Request, status

from app.schemas.common import ApiResponse, ListResponse
from app.schemas.jobs import JobCreateRequest, JobRecord
from app.services.job_service import create_mock_job, get_mock_job, list_mock_jobs


router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=ApiResponse[JobRecord], status_code=status.HTTP_201_CREATED)
async def create_job(
    request: Request, payload: JobCreateRequest
) -> dict[str, object]:
    job = create_mock_job(payload)
    return {"data": job, "request_id": request.state.request_id}


@router.get("", response_model=ApiResponse[ListResponse[JobRecord]])
async def list_jobs(request: Request) -> dict[str, object]:
    items = list_mock_jobs()
    return {
        "data": ListResponse(items=items, total=len(items)),
        "request_id": request.state.request_id,
    }


@router.get("/{jd_id}", response_model=ApiResponse[JobRecord])
async def get_job(request: Request, jd_id: str) -> dict[str, object]:
    job = get_mock_job(jd_id)
    return {"data": job, "request_id": request.state.request_id}
