from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.job import JobDescription, JobProfile as JobProfileModel
from app.schemas.jobs import JobCreateRequest, JobProfile, JobRecord


def _next_job_id(db: Session) -> str:
    count = db.scalar(select(func.count()).select_from(JobDescription)) or 0
    return f"jd_{count + 1:04d}"


def _next_profile_id(jd_id: str, profile_version: int) -> str:
    return f"profile_{jd_id}_{profile_version:04d}"


def _to_job_profile(profile: JobProfileModel) -> JobProfile:
    return JobProfile(
        job_profile_id=profile.id,
        role_category=profile.role_category,
        required_skills=list(profile.required_skills or []),
        preferred_skills=list(profile.preferred_skills or []),
        responsibilities=list(profile.responsibilities or []),
        business_scenarios=list(profile.business_scenarios or []),
        hidden_requirements=list(profile.hidden_requirements or []),
        interview_focus=list(profile.interview_focus or []),
        risk_level=profile.risk_level,
        summary=profile.summary,
    )


def _to_job_record(job: JobDescription, profile: JobProfileModel) -> JobRecord:
    return JobRecord(
        jd_id=job.id,
        company=job.company,
        job_title=job.job_title,
        location=job.location,
        raw_text=job.raw_text,
        source_url=job.source_url,
        job_profile=_to_job_profile(profile),
    )


def _latest_profile(db: Session, jd_id: str) -> JobProfileModel | None:
    return db.scalars(
        select(JobProfileModel)
        .where(JobProfileModel.jd_id == jd_id)
        .order_by(JobProfileModel.profile_version.desc(), JobProfileModel.created_at.desc())
        .limit(1)
    ).first()


def create_job_with_profile(
    db: Session,
    *,
    payload: JobCreateRequest,
    profile: JobProfile,
) -> JobRecord:
    jd_id = _next_job_id(db)
    profile_version = 1
    job = JobDescription(
        id=jd_id,
        user_id="default",
        company=payload.company,
        job_title=payload.job_title,
        location=payload.location,
        source_url=str(payload.source_url) if payload.source_url else None,
        raw_text=payload.raw_text,
        status="active",
    )
    job_profile = JobProfileModel(
        id=_next_profile_id(jd_id, profile_version),
        jd_id=jd_id,
        profile_version=profile_version,
        role_category=profile.role_category,
        required_skills=profile.required_skills,
        preferred_skills=profile.preferred_skills,
        responsibilities=profile.responsibilities,
        business_scenarios=profile.business_scenarios,
        hidden_requirements=profile.hidden_requirements,
        interview_focus=profile.interview_focus,
        risk_level=profile.risk_level,
        summary=profile.summary,
    )

    try:
        db.add(job)
        db.add(job_profile)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(job)
    db.refresh(job_profile)
    return _to_job_record(job, job_profile)


def list_jobs(db: Session) -> list[JobRecord]:
    jobs = db.scalars(
        select(JobDescription)
        .where(JobDescription.status == "active")
        .order_by(JobDescription.created_at)
    ).all()
    records: list[JobRecord] = []
    for job in jobs:
        profile = _latest_profile(db, job.id)
        if profile:
            records.append(_to_job_record(job, profile))
    return records


def get_job(db: Session, jd_id: str) -> JobRecord:
    job = db.get(JobDescription, jd_id)
    if not job or job.status != "active":
        raise AppError(
            code="job_not_found",
            message="JD was not found.",
            status_code=404,
            details={"jd_id": jd_id},
        )
    profile = _latest_profile(db, jd_id)
    if not profile:
        raise AppError(
            code="job_not_found",
            message="JD profile was not found.",
            status_code=404,
            details={"jd_id": jd_id},
        )
    return _to_job_record(job, profile)


def get_job_with_profile(db: Session, jd_id: str) -> JobRecord:
    return get_job(db, jd_id)
