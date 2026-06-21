from hashlib import sha256
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.repositories import resume_repository
from app.schemas.resumes import ResumeRecord, StructuredResume
from app.services.text_extraction_service import extract_resume_text


SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".md": "markdown",
    ".markdown": "markdown",
    ".txt": "text",
}
ALLOWED_MIME_TYPES = {
    "pdf": {"application/pdf"},
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    },
    "markdown": {"text/markdown", "text/plain", "application/octet-stream"},
    "text": {"text/plain", "application/octet-stream"},
}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def detect_file_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    file_type = SUPPORTED_EXTENSIONS.get(suffix)
    if not file_type:
        raise AppError(
            code="unsupported_resume_file_type",
            message="Supported resume file types are PDF, DOCX, Markdown, and text.",
            status_code=400,
            details={"filename": filename},
        )
    return file_type


def validate_resume_upload(
    filename: str, content_type: str | None, content: bytes
) -> str:
    file_type = detect_file_type(filename)
    if not content:
        raise AppError(
            code="resume_file_empty",
            message="Resume file is empty.",
            status_code=400,
            details={"filename": filename},
        )
    if len(content) > MAX_UPLOAD_BYTES:
        raise AppError(
            code="resume_file_too_large",
            message="Resume file exceeds the Phase 1C upload size limit.",
            status_code=413,
            details={"max_bytes": MAX_UPLOAD_BYTES},
        )
    if content_type and content_type not in ALLOWED_MIME_TYPES[file_type]:
        raise AppError(
            code="resume_file_mime_mismatch",
            message="Resume MIME type does not match the file extension.",
            status_code=400,
            details={
                "filename": filename,
                "content_type": content_type,
                "file_type": file_type,
            },
        )
    return file_type


def extract_mock_skills(text: str) -> dict[str, list[str]]:
    lowered = text.lower()
    skills = {
        "programming": [],
        "backend": [],
        "frontend": [],
        "ai": [],
        "database": [],
        "tools": [],
    }
    if "python" in lowered:
        skills["programming"].append("Python")
    if "typescript" in lowered:
        skills["programming"].append("TypeScript")
    if "fastapi" in lowered:
        skills["backend"].append("FastAPI")
    if "react" in lowered:
        skills["frontend"].append("React")
    if "rag" in lowered:
        skills["ai"].append("RAG")
    if "sql" in lowered:
        skills["database"].append("SQL")
    if "docker" in lowered:
        skills["tools"].append("Docker")
    return skills


def create_resume(
    db: Session, filename: str, content_type: str | None, content: bytes
) -> ResumeRecord:
    file_type = validate_resume_upload(filename, content_type, content)
    extraction = extract_resume_text(filename, file_type, content_type, content)
    raw_text = extraction.raw_text
    structured_resume = StructuredResume(
        basic_info={"name": None, "email": None, "phone": None, "location": None},
        skills=extract_mock_skills(raw_text),
    )
    return resume_repository.create_resume_with_initial_version(
        db,
        filename=filename,
        file_type=file_type,
        text_hash=sha256(content).hexdigest(),
        raw_text=raw_text,
        raw_text_preview=raw_text[:500],
        structured_resume=structured_resume,
        extraction_status=extraction.extraction_status,
        extraction_method=extraction.extraction_method,
        extraction_warnings=extraction.warnings,
        risk_flags=[],
    )


def list_resumes(db: Session) -> list[ResumeRecord]:
    return resume_repository.list_resumes(db)


def get_resume(db: Session, resume_id: str) -> ResumeRecord:
    return resume_repository.get_resume(db, resume_id)
