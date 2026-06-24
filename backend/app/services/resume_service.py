from hashlib import sha256
from pathlib import Path
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.repositories import resume_repository
from app.schemas.resumes import (
    ResumeParseRequest,
    ResumeParseResult,
    ResumeRecord,
    ResumeRiskCheckRequest,
    ResumeRiskCheckResult,
    ResumeVersionCloneRequest,
    ResumeVersionCreateRequest,
    ResumeVersionRecord,
    StructuredResume,
)
from app.services.resume_parser_service import PARSER_METHOD, parse_structured_resume
from app.services.resume_risk_service import evaluate_resume_risks
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
VERSION_NAME_MAX_LENGTH = 200
TARGET_ROLE_MAX_LENGTH = 160


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


def create_resume(
    db: Session, filename: str, content_type: str | None, content: bytes
) -> ResumeRecord:
    file_type = validate_resume_upload(filename, content_type, content)
    extraction = extract_resume_text(filename, file_type, content_type, content)
    raw_text = extraction.raw_text
    structured_resume = parse_structured_resume(raw_text)
    return resume_repository.create_resume_with_initial_version(
        db,
        filename=filename,
        file_type=file_type,
        text_hash=sha256(content).hexdigest(),
        parse_status="parsed",
        raw_text=raw_text,
        raw_text_preview=raw_text[:500],
        structured_resume=structured_resume,
        extraction_status=extraction.extraction_status,
        extraction_method=extraction.extraction_method,
        extraction_warnings=extraction.warnings,
        risk_flags=[],
        risk_report={},
    )


def list_resumes(db: Session) -> list[ResumeRecord]:
    return resume_repository.list_resumes(db)


def get_resume(db: Session, resume_id: str) -> ResumeRecord:
    return resume_repository.get_resume(db, resume_id)


def parse_resume(
    db: Session, resume_id: str, payload: ResumeParseRequest | None = None
) -> ResumeParseResult:
    request = payload or ResumeParseRequest()
    source = resume_repository.get_source_resume_version(
        db, resume_id, request.resume_version_id
    )
    raw_text = source.raw_text.strip()
    if not raw_text:
        raise AppError(
            code="resume_raw_text_empty",
            message="Resume raw text is empty and cannot be parsed.",
            status_code=400,
            details={"resume_id": resume_id, "version_id": source.id},
        )
    return ResumeParseResult(
        resume_id=resume_id,
        source_version_id=source.id,
        raw_text_preview=source.raw_text_preview,
        structured_resume=parse_structured_resume(raw_text),
        extraction_method=PARSER_METHOD,
        extraction_warnings=list(source.extraction_warnings or []),
        parsed_at=_utc_now(),
    )


def check_resume_risk(
    db: Session, resume_id: str, payload: ResumeRiskCheckRequest | None = None
) -> ResumeRiskCheckResult:
    request = payload or ResumeRiskCheckRequest()
    source_version_id: str | None = None

    if request.structured_resume is not None:
        if request.resume_version_id:
            source = resume_repository.get_source_resume_version(
                db, resume_id, request.resume_version_id
            )
            source_version_id = source.id
        else:
            resume_repository.get_resume(db, resume_id)
        structured_resume = request.structured_resume
    else:
        source = resume_repository.get_source_resume_version(
            db, resume_id, request.resume_version_id
        )
        source_version_id = source.id
        structured_resume = StructuredResume.model_validate(source.structured_resume)

    risk_flags, risk_report = evaluate_resume_risks(structured_resume)
    return ResumeRiskCheckResult(
        resume_id=resume_id,
        source_version_id=source_version_id,
        risk_flags=risk_flags,
        risk_report=risk_report,
        checked_at=_utc_now(),
    )


def _normalize_optional_text(
    value: str | None, max_length: int, field_name: str
) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > max_length:
        raise AppError(
            code="validation_error",
            message=f"{field_name} is too long.",
            status_code=400,
            details={"field": field_name, "max_length": max_length},
        )
    return normalized


def _normalize_required_text(value: str, max_length: int, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise AppError(
            code="validation_error",
            message=f"{field_name} is required.",
            status_code=400,
            details={"field": field_name},
        )
    if len(normalized) > max_length:
        raise AppError(
            code="validation_error",
            message=f"{field_name} is too long.",
            status_code=400,
            details={"field": field_name, "max_length": max_length},
        )
    return normalized


def save_confirmed_resume_version(
    db: Session, resume_id: str, payload: ResumeVersionCreateRequest
) -> ResumeVersionRecord:
    version_name = _normalize_required_text(
        payload.version_name, VERSION_NAME_MAX_LENGTH, "version_name"
    )
    target_role = _normalize_optional_text(
        payload.target_role, TARGET_ROLE_MAX_LENGTH, "target_role"
    )
    risk_report = payload.risk_report
    if risk_report is None:
        risk_flags, risk_report = evaluate_resume_risks(payload.structured_resume)
        risk_flag_dicts = [flag.model_dump() for flag in risk_flags]
    else:
        risk_report = dict(risk_report)
        risk_flag_dicts = _risk_flags_from_report(risk_report)

    return resume_repository.create_confirmed_resume_version(
        db,
        resume_id,
        source_version_id=payload.source_version_id,
        version_name=version_name,
        target_role=target_role,
        structured_resume=payload.structured_resume,
        risk_flags=risk_flag_dicts,
        risk_report=risk_report,
    )


def _risk_flags_from_report(risk_report: dict[str, object]) -> list[dict[str, object]]:
    flags = risk_report.get("flags") or risk_report.get("risk_flags")
    if not isinstance(flags, list):
        return []
    return [flag for flag in flags if isinstance(flag, dict)]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def list_resume_versions(db: Session, resume_id: str) -> list[ResumeVersionRecord]:
    return resume_repository.list_resume_versions(db, resume_id)


def get_resume_version(db: Session, version_id: str) -> ResumeVersionRecord:
    return resume_repository.get_resume_version(db, version_id)


def clone_resume_version(
    db: Session, version_id: str, payload: ResumeVersionCloneRequest
) -> ResumeVersionRecord:
    version_name = _normalize_optional_text(
        payload.version_name, VERSION_NAME_MAX_LENGTH, "version_name"
    )
    target_role = _normalize_optional_text(
        payload.target_role, TARGET_ROLE_MAX_LENGTH, "target_role"
    )
    return resume_repository.clone_resume_version(
        db,
        version_id,
        version_name=version_name,
        target_role=target_role,
    )


def archive_resume_version(db: Session, version_id: str) -> ResumeVersionRecord:
    return resume_repository.archive_resume_version(db, version_id)
