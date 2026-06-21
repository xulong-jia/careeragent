from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.resume import Resume, ResumeVersion
from app.schemas.resumes import ResumeRecord, SourceFile, StructuredResume


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
        parse_status="mock_parsed",
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
    )


def _latest_version(db: Session, resume_id: str) -> ResumeVersion | None:
    return db.scalars(
        select(ResumeVersion)
        .where(ResumeVersion.resume_id == resume_id)
        .where(ResumeVersion.status == "active")
        .order_by(ResumeVersion.version_number.desc(), ResumeVersion.created_at.desc())
        .limit(1)
    ).first()


def create_resume_with_initial_version(
    db: Session,
    *,
    filename: str,
    file_type: str,
    text_hash: str,
    raw_text: str,
    raw_text_preview: str,
    structured_resume: StructuredResume,
    extraction_status: str,
    extraction_method: str,
    extraction_warnings: list[str],
    risk_flags: list[dict[str, object]],
) -> ResumeRecord:
    resume_id = _next_resume_id(db)
    resume = Resume(
        id=resume_id,
        user_id="default",
        title=filename,
        original_filename=filename,
        file_type=file_type,
        source_file_hash=text_hash,
        status="active",
    )
    version = ResumeVersion(
        id=_next_resume_version_id(resume_id, 1),
        resume_id=resume_id,
        version_name="Initial version",
        version_number=1,
        raw_text=raw_text,
        raw_text_preview=raw_text_preview,
        structured_resume=structured_resume.model_dump(),
        extraction_status=extraction_status,
        extraction_method=extraction_method,
        extraction_warnings=extraction_warnings,
        risk_flags=risk_flags,
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
