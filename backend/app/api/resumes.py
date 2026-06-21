from hashlib import sha256
from pathlib import Path

from fastapi import APIRouter, Request, UploadFile, status

from app.core.errors import AppError
from app.schemas.common import ApiResponse, ListResponse
from app.schemas.resumes import ResumeRecord, SourceFile, StructuredResume
from app.services.mock_store import store


router = APIRouter(prefix="/api/resumes", tags=["resumes"])

SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".md": "markdown",
    ".markdown": "markdown",
}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def detect_file_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    file_type = SUPPORTED_EXTENSIONS.get(suffix)
    if not file_type:
        raise AppError(
            code="unsupported_resume_file_type",
            message="Supported resume file types are PDF, DOCX, and Markdown.",
            status_code=400,
            details={"filename": filename},
        )
    return file_type


def build_mock_resume(filename: str, file_type: str, content: bytes) -> ResumeRecord:
    resume_id = store.next_id("resume", len(store.resumes))
    text_hash = sha256(content).hexdigest()
    structured_resume = StructuredResume(
        basic_info={"name": None, "email": None, "phone": None, "location": None},
        skills={
            "programming": [],
            "backend": [],
            "frontend": [],
            "ai": [],
            "database": [],
            "tools": [],
        },
    )
    return ResumeRecord(
        resume_id=resume_id,
        filename=filename,
        file_type=file_type,
        parse_status="mock_parsed",
        raw_text="Mock resume raw text placeholder. No real resume content is stored.",
        structured_resume=structured_resume,
        source_file=SourceFile(
            filename=filename,
            file_type=file_type,
            text_hash=text_hash,
        ),
        risk_flags=[],
    )


@router.post(
    "/upload",
    response_model=ApiResponse[ResumeRecord],
    status_code=status.HTTP_201_CREATED,
)
async def upload_resume(request: Request, file: UploadFile) -> dict[str, object]:
    file_type = detect_file_type(file.filename or "")
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise AppError(
            code="resume_file_too_large",
            message="Resume file exceeds the Phase 1A upload size limit.",
            status_code=413,
            details={"max_bytes": MAX_UPLOAD_BYTES},
        )

    resume = build_mock_resume(file.filename or "resume", file_type, content)
    store.resumes[resume.resume_id] = resume
    return {"data": resume, "request_id": request.state.request_id}


@router.get("", response_model=ApiResponse[ListResponse[ResumeRecord]])
async def list_resumes(request: Request) -> dict[str, object]:
    items = list(store.resumes.values())
    return {
        "data": ListResponse(items=items, total=len(items)),
        "request_id": request.state.request_id,
    }


@router.get("/{resume_id}", response_model=ApiResponse[ResumeRecord])
async def get_resume(request: Request, resume_id: str) -> dict[str, object]:
    resume = store.resumes.get(resume_id)
    if not resume:
        raise AppError(
            code="resume_not_found",
            message="Resume was not found in the Phase 1A mock store.",
            status_code=404,
            details={"resume_id": resume_id},
        )
    return {"data": resume, "request_id": request.state.request_id}
