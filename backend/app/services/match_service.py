from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.job import JobDescription, JobProfile
from app.models.resume import Resume, ResumeVersion
from app.repositories import match_repository
from app.schemas.matches import MatchEvidence, MatchReport, MatchRunRequest


def flatten_resume_skills(structured_resume: dict[str, object]) -> set[str]:
    flattened: set[str] = set()
    skills = structured_resume.get("skills")
    if not isinstance(skills, dict):
        return flattened
    for values in skills.values():
        if isinstance(values, list):
            flattened.update(str(value) for value in values)
    return flattened


def _get_resume(db: Session, resume_id: str) -> Resume:
    resume = db.get(Resume, resume_id)
    if not resume or resume.status != "active":
        raise AppError(
            code="resume_not_found",
            message="Resume was not found.",
            status_code=404,
            details={"resume_id": resume_id},
        )
    return resume


def _get_resume_version(db: Session, resume_version_id: str) -> ResumeVersion:
    version = db.get(ResumeVersion, resume_version_id)
    if not version:
        raise AppError(
            code="resume_version_not_found",
            message="Resume version was not found.",
            status_code=404,
            details={"resume_version_id": resume_version_id},
        )
    return version


def _latest_active_resume_version(db: Session, resume_id: str) -> ResumeVersion:
    _get_resume(db, resume_id)
    version = (
        db.query(ResumeVersion)
        .filter(ResumeVersion.resume_id == resume_id)
        .filter(ResumeVersion.status == "active")
        .order_by(ResumeVersion.version_number.desc(), ResumeVersion.created_at.desc())
        .first()
    )
    if not version:
        raise AppError(
            code="resume_version_not_found",
            message="Active resume version was not found.",
            status_code=404,
            details={"resume_id": resume_id},
        )
    return version


def _resolve_resume_version(db: Session, payload: MatchRunRequest) -> ResumeVersion:
    if payload.resume_version_id:
        version = _get_resume_version(db, payload.resume_version_id)
        if payload.resume_id:
            _get_resume(db, payload.resume_id)
            if version.resume_id != payload.resume_id:
                raise AppError(
                    code="resume_version_mismatch",
                    message="Resume version does not belong to the given resume.",
                    status_code=400,
                    details={
                        "resume_id": payload.resume_id,
                        "resume_version_id": payload.resume_version_id,
                    },
                )
        return version

    if not payload.resume_id:
        raise AppError(
            code="validation_error",
            message="Either resume_id or resume_version_id is required.",
            status_code=422,
            details={"fields": ["resume_id", "resume_version_id"]},
        )
    return _latest_active_resume_version(db, payload.resume_id)


def _latest_job_profile(db: Session, jd_id: str) -> tuple[JobDescription, JobProfile]:
    job = db.get(JobDescription, jd_id)
    if not job or job.status != "active":
        raise AppError(
            code="job_not_found",
            message="JD was not found.",
            status_code=404,
            details={"jd_id": jd_id},
        )
    profile = (
        db.query(JobProfile)
        .filter(JobProfile.jd_id == jd_id)
        .order_by(JobProfile.profile_version.desc(), JobProfile.created_at.desc())
        .first()
    )
    if not profile:
        raise AppError(
            code="job_not_found",
            message="JD profile was not found.",
            status_code=404,
            details={"jd_id": jd_id},
        )
    return job, profile


def run_match_report(db: Session, payload: MatchRunRequest) -> MatchReport:
    resume_version = _resolve_resume_version(db, payload)
    _, job_profile = _latest_job_profile(db, payload.jd_id)
    resume_skills = flatten_resume_skills(resume_version.structured_resume)
    required_skills = set(job_profile.required_skills or [])
    matched_skills = sorted(required_skills & resume_skills)
    missing_skills = sorted(required_skills - resume_skills)
    coverage = len(matched_skills) / len(required_skills) if required_skills else 0

    skill_score = 55 + round(40 * coverage)
    dimension_scores = {
        "skill_match": skill_score,
        "project_relevance": 65 if matched_skills else 55,
        "business_understanding": 60,
        "expression_quality": 62,
        "education_fit": 60,
        "risk_control": 80,
    }
    total_score = round(sum(dimension_scores.values()) / len(dimension_scores))

    return match_repository.create_match_report(
        db,
        resume_version_id=resume_version.id,
        jd_id=payload.jd_id,
        job_profile_id=job_profile.id,
        total_score=total_score,
        dimension_scores=dimension_scores,
        evidence=[
            MatchEvidence(
                dimension="skill_match",
                jd_requirement=", ".join(sorted(required_skills)) or "unspecified",
                resume_signal=", ".join(matched_skills) if matched_skills else None,
                score_impact="positive" if matched_skills else "neutral",
            )
        ],
        strengths=[
            "Matched required skills: " + ", ".join(matched_skills)
            if matched_skills
            else "Resume file passed Phase 1 validation."
        ],
        gaps=[
            "Missing required skills: " + ", ".join(missing_skills)
            if missing_skills
            else "No required skill gap detected by deterministic mock rules."
        ],
        rewrite_priorities=[
            "Confirm project facts and evidence before rewriting resume bullets."
        ],
        risk_flags=[],
    )


def list_match_reports(
    db: Session,
    *,
    jd_id: str | None = None,
    resume_version_id: str | None = None,
) -> list[MatchReport]:
    return match_repository.list_match_reports(
        db,
        jd_id=jd_id,
        resume_version_id=resume_version_id,
    )


def get_match_report(db: Session, match_report_id: str) -> MatchReport:
    return match_repository.get_match_report(db, match_report_id)
