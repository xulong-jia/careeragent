from hashlib import sha256
from pathlib import Path

from app.core.errors import AppError
from app.schemas.resumes import ResumeRecord, SourceFile, StructuredResume
from app.services.mock_store import store


SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".md": "markdown",
    ".markdown": "markdown",
}
ALLOWED_MIME_TYPES = {
    "pdf": {"application/pdf"},
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    },
    "markdown": {"text/markdown", "text/plain", "application/octet-stream"},
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
            message="Resume file exceeds the Phase 1B upload size limit.",
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


def extract_mock_resume_text(file_type: str, content: bytes) -> str:
    if file_type == "markdown":
        text = content.decode("utf-8", errors="ignore").strip()
        return text or "Mock markdown resume text placeholder."
    return "Mock resume raw text placeholder. No real resume content is stored."


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


def create_mock_resume(
    filename: str, content_type: str | None, content: bytes
) -> ResumeRecord:
    file_type = validate_resume_upload(filename, content_type, content)
    resume_id = store.next_id("resume", len(store.resumes))
    raw_text = extract_mock_resume_text(file_type, content)
    structured_resume = StructuredResume(
        basic_info={"name": None, "email": None, "phone": None, "location": None},
        skills=extract_mock_skills(raw_text),
    )
    resume = ResumeRecord(
        resume_id=resume_id,
        filename=filename,
        file_type=file_type,
        parse_status="mock_parsed",
        raw_text=raw_text,
        structured_resume=structured_resume,
        source_file=SourceFile(
            filename=filename,
            file_type=file_type,
            text_hash=sha256(content).hexdigest(),
        ),
        risk_flags=[],
    )
    store.resumes[resume.resume_id] = resume
    return resume


def list_mock_resumes() -> list[ResumeRecord]:
    return list(store.resumes.values())


def get_mock_resume(resume_id: str) -> ResumeRecord:
    resume = store.resumes.get(resume_id)
    if not resume:
        raise AppError(
            code="resume_not_found",
            message="Resume was not found in the Phase 1B mock store.",
            status_code=404,
            details={"resume_id": resume_id},
        )
    return resume
