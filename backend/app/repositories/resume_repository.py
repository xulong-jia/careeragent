from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.resume import Resume, ResumeVersion
from app.schemas.resumes import (
    ResumeRecord,
    ResumeVersionRecord,
    SourceFile,
    StructuredResume,
)


ARCHIVED_STATUS = "archived"
CONFIRMED_STATUS = "confirmed"


def _next_resume_id(db: Session) -> str:
    count = db.scalar(select(func.count()).select_from(Resume)) or 0
    return f"resume_{count + 1:04d}"


def _next_resume_version_id(resume_id: str, version_number: int) -> str:
    return f"{resume_id}_version_{version_number:04d}"


def _to_resume_record(resume: Resume, version: ResumeVersion) -> ResumeRecord:
    return ResumeRecord(
        resume_id=resume.id,
        filename=resume.original_filename,
        file_type=resume.file_type,
        parse_status=resume.parse_status,
        raw_text=version.raw_text,
        raw_text_preview=version.raw_text_preview,
        extraction_status=version.extraction_status,
        extraction_method=version.extraction_method,
        extraction_warnings=list(version.extraction_warnings or []),
        structured_resume=StructuredResume.model_validate(version.structured_resume),
        source_file=SourceFile(
            filename=resume.original_filename,
            file_type=resume.file_type,
            text_hash=resume.source_file_hash,
        ),
        risk_flags=list(version.risk_flags or []),
        risk_report=dict(version.risk_report or {}),
    )


def _to_resume_version_record(version: ResumeVersion) -> ResumeVersionRecord:
    return ResumeVersionRecord(
        resume_version_id=version.id,
        resume_id=version.resume_id,
        version_name=version.version_name,
        version_number=version.version_number,
        target_role=version.target_role,
        raw_text=version.raw_text,
        raw_text_preview=version.raw_text_preview,
        structured_resume=StructuredResume.model_validate(version.structured_resume),
        extraction_status=version.extraction_status,
        extraction_method=version.extraction_method,
        extraction_warnings=list(version.extraction_warnings or []),
        risk_flags=list(version.risk_flags or []),
        risk_report=dict(version.risk_report or {}),
        status=version.status,
        is_archived=version.status == "archived",
        created_at=version.created_at,
        archived_at=version.archived_at,
    )


def _latest_version(db: Session, resume_id: str) -> ResumeVersion | None:
    return db.scalars(
        select(ResumeVersion)
        .where(ResumeVersion.resume_id == resume_id)
        .where(ResumeVersion.status != ARCHIVED_STATUS)
        .order_by(ResumeVersion.version_number.desc(), ResumeVersion.created_at.desc())
        .limit(1)
    ).first()


def create_resume_with_initial_version(
    db: Session,
    *,
    filename: str,
    file_type: str,
    text_hash: str,
    parse_status: str,
    raw_text: str,
    raw_text_preview: str,
    structured_resume: StructuredResume,
    extraction_status: str,
    extraction_method: str,
    extraction_warnings: list[str],
    risk_flags: list[dict[str, object]],
    risk_report: dict[str, object] | None = None,
) -> ResumeRecord:
    resume_id = _next_resume_id(db)
    resume = Resume(
        id=resume_id,
        user_id="default",
        title=filename,
        original_filename=filename,
        file_type=file_type,
        source_file_hash=text_hash,
        parse_status=parse_status,
        status="active",
    )
    version = ResumeVersion(
        id=_next_resume_version_id(resume_id, 1),
        resume_id=resume_id,
        version_name="Initial version",
        version_number=1,
        target_role=None,
        raw_text=raw_text,
        raw_text_preview=raw_text_preview,
        structured_resume=structured_resume.model_dump(),
        extraction_status=extraction_status,
        extraction_method=extraction_method,
        extraction_warnings=extraction_warnings,
        risk_flags=risk_flags,
        risk_report=risk_report or {},
        status="active",
    )

    try:
        db.add(resume)
        db.add(version)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(resume)
    db.refresh(version)
    return _to_resume_record(resume, version)


def list_resumes(db: Session) -> list[ResumeRecord]:
    resumes = db.scalars(
        select(Resume).where(Resume.status == "active").order_by(Resume.created_at)
    ).all()
    records: list[ResumeRecord] = []
    for resume in resumes:
        version = _latest_version(db, resume.id)
        if version:
            records.append(_to_resume_record(resume, version))
    return records


def get_resume(db: Session, resume_id: str) -> ResumeRecord:
    resume = db.get(Resume, resume_id)
    if not resume or resume.status != "active":
        raise AppError(
            code="resume_not_found",
            message="Resume was not found.",
            status_code=404,
            details={"resume_id": resume_id},
        )
    version = _latest_version(db, resume_id)
    if not version:
        raise AppError(
            code="resume_not_found",
            message="Resume version was not found.",
            status_code=404,
            details={"resume_id": resume_id},
        )
    return _to_resume_record(resume, version)


def get_resume_with_latest_version(db: Session, resume_id: str) -> ResumeRecord:
    return get_resume(db, resume_id)


def list_resume_versions(db: Session, resume_id: str) -> list[ResumeVersionRecord]:
    resume = db.get(Resume, resume_id)
    if not resume or resume.status != "active":
        raise AppError(
            code="resume_not_found",
            message="Resume was not found.",
            status_code=404,
            details={"resume_id": resume_id},
        )
    versions = db.scalars(
        select(ResumeVersion)
        .where(ResumeVersion.resume_id == resume_id)
        .order_by(ResumeVersion.version_number, ResumeVersion.created_at)
    ).all()
    return [_to_resume_version_record(version) for version in versions]


def get_resume_version(db: Session, version_id: str) -> ResumeVersionRecord:
    version = db.get(ResumeVersion, version_id)
    if not version:
        raise AppError(
            code="resume_version_not_found",
            message="Resume version was not found.",
            status_code=404,
            details={"version_id": version_id},
        )
    return _to_resume_version_record(version)


def clone_resume_version(
    db: Session,
    version_id: str,
    *,
    version_name: str | None = None,
    target_role: str | None = None,
) -> ResumeVersionRecord:
    source = db.get(ResumeVersion, version_id)
    if not source:
        raise AppError(
            code="resume_version_not_found",
            message="Resume version was not found.",
            status_code=404,
            details={"version_id": version_id},
        )

    max_version_number = (
        db.scalar(
            select(func.max(ResumeVersion.version_number)).where(
                ResumeVersion.resume_id == source.resume_id
            )
        )
        or 0
    )
    next_version_number = max_version_number + 1
    default_version_name = f"Copy of {source.version_name}"
    if len(default_version_name) > 200:
        default_version_name = f"Version {next_version_number}"
    cloned_version = ResumeVersion(
        id=_next_resume_version_id(source.resume_id, next_version_number),
        resume_id=source.resume_id,
        version_name=version_name or default_version_name,
        version_number=next_version_number,
        target_role=target_role if target_role is not None else source.target_role,
        raw_text=source.raw_text,
        raw_text_preview=source.raw_text_preview,
        structured_resume=source.structured_resume,
        extraction_status=source.extraction_status,
        extraction_method=source.extraction_method,
        extraction_warnings=list(source.extraction_warnings or []),
        risk_flags=list(source.risk_flags or []),
        risk_report=dict(source.risk_report or {}),
        status="active",
        archived_at=None,
    )

    try:
        db.add(cloned_version)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(cloned_version)
    return _to_resume_version_record(cloned_version)


def archive_resume_version(db: Session, version_id: str) -> ResumeVersionRecord:
    version = db.get(ResumeVersion, version_id)
    if not version:
        raise AppError(
            code="resume_version_not_found",
            message="Resume version was not found.",
            status_code=404,
            details={"version_id": version_id},
        )

    if version.status != ARCHIVED_STATUS:
        version.status = ARCHIVED_STATUS
        version.archived_at = datetime.now(timezone.utc).replace(tzinfo=None)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
        db.refresh(version)
    return _to_resume_version_record(version)


def get_source_resume_version(
    db: Session, resume_id: str, version_id: str | None = None
) -> ResumeVersion:
    resume = db.get(Resume, resume_id)
    if not resume or resume.status != "active":
        raise AppError(
            code="resume_not_found",
            message="Resume was not found.",
            status_code=404,
            details={"resume_id": resume_id},
        )

    if version_id:
        version = db.get(ResumeVersion, version_id)
        if not version:
            raise AppError(
                code="resume_version_not_found",
                message="Resume version was not found.",
                status_code=404,
                details={"version_id": version_id},
            )
        if version.resume_id != resume_id:
            raise AppError(
                code="resume_version_resume_mismatch",
                message="Resume version does not belong to the requested resume.",
                status_code=400,
                details={"resume_id": resume_id, "version_id": version_id},
            )
        return version

    version = _latest_version(db, resume_id)
    if not version:
        raise AppError(
            code="resume_version_not_found",
            message="Resume version was not found.",
            status_code=404,
            details={"resume_id": resume_id},
        )
    return version


def create_confirmed_resume_version(
    db: Session,
    resume_id: str,
    *,
    source_version_id: str | None,
    version_name: str,
    target_role: str | None,
    structured_resume: StructuredResume,
    risk_flags: list[dict[str, object]],
    risk_report: dict[str, object],
) -> ResumeVersionRecord:
    source = get_source_resume_version(db, resume_id, source_version_id)
    max_version_number = (
        db.scalar(
            select(func.max(ResumeVersion.version_number)).where(
                ResumeVersion.resume_id == resume_id
            )
        )
        or 0
    )
    next_version_number = max_version_number + 1
    version = ResumeVersion(
        id=_next_resume_version_id(resume_id, next_version_number),
        resume_id=resume_id,
        version_name=version_name,
        version_number=next_version_number,
        target_role=target_role,
        raw_text=source.raw_text,
        raw_text_preview=source.raw_text_preview,
        structured_resume=structured_resume.model_dump(),
        extraction_status=source.extraction_status,
        extraction_method=source.extraction_method,
        extraction_warnings=list(source.extraction_warnings or []),
        risk_flags=risk_flags,
        risk_report=risk_report,
        status=CONFIRMED_STATUS,
        archived_at=None,
    )

    try:
        db.add(version)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(version)
    return _to_resume_version_record(version)
