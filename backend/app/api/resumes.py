from fastapi import APIRouter, Request, UploadFile, status

from app.schemas.common import ApiResponse, ListResponse
from app.schemas.resumes import ResumeRecord
from app.services.resume_service import (
    create_mock_resume,
    get_mock_resume,
    list_mock_resumes,
)


router = APIRouter(prefix="/api/resumes", tags=["resumes"])


@router.post(
    "/upload",
    response_model=ApiResponse[ResumeRecord],
    status_code=status.HTTP_201_CREATED,
)
async def upload_resume(request: Request, file: UploadFile) -> dict[str, object]:
    content = await file.read()
    resume = create_mock_resume(file.filename or "", file.content_type, content)
    return {"data": resume, "request_id": request.state.request_id}


@router.get("", response_model=ApiResponse[ListResponse[ResumeRecord]])
async def list_resumes(request: Request) -> dict[str, object]:
    items = list_mock_resumes()
    return {
        "data": ListResponse(items=items, total=len(items)),
        "request_id": request.state.request_id,
    }


@router.get("/{resume_id}", response_model=ApiResponse[ResumeRecord])
async def get_resume(request: Request, resume_id: str) -> dict[str, object]:
    resume = get_mock_resume(resume_id)
    return {"data": resume, "request_id": request.state.request_id}
