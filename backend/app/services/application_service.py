from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.agent import AgentRun
from app.models.job import JobDescription, JobProfile
from app.models.match import MatchReport as MatchReportModel
from app.models.resume import ResumeVersion
from app.repositories import application_repository
from app.schemas.applications import (
    ApplicationCreateRequest,
    ApplicationRecord,
    ApplicationStats,
    ApplicationUpdateRequest,
)


APPLICATION_STATUSES = {
    "saved",
    "ready_to_apply",
    "applied",
    "written_test",
    "first_interview",
    "second_interview",
    "hr_interview",
    "offer",
    "rejected",
    "withdrawn",
    "archived",
}
INTERVIEW_STATUSES = {"first_interview", "second_interview", "hr_interview"}
INACTIVE_STATUSES = {"offer", "rejected", "withdrawn", "archived"}


def _invalid_field(field: str, message: str) -> AppError:
    return AppError(
        code="application_invalid_field",
        message=message,
        status_code=400,
        details={"field": field},
    )


def _normalize_required_text(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise _invalid_field(field, f"{field} is required.")
    return normalized


def _normalize_optional_text(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_status(value: str) -> str:
    normalized = _normalize_required_text(value, "status").lower()
    if normalized not in APPLICATION_STATUSES:
        raise _invalid_field("status", "Unsupported application status.")
    return normalized


def _normalize_tags(tags: list[str] | None) -> list[str]:
    normalized: list[str] = []
    for tag in tags or []:
        value = str(tag).strip()
        if value and value not in normalized:
            normalized.append(value)
    return normalized


def _latest_job_profile_role_category(db: Session, jd_id: str | None) -> str | None:
    if not jd_id:
        return None
    profile = db.scalars(
        select(JobProfile)
        .where(JobProfile.jd_id == jd_id)
        .order_by(JobProfile.profile_version.desc(), JobProfile.created_at.desc())
        .limit(1)
    ).first()
    return profile.role_category if profile else None


def _validate_and_resolve_refs(
    db: Session,
    *,
    jd_id: str | None,
    resume_version_id: str | None,
    match_report_id: str | None,
    agent_run_id: str | None = None,
) -> tuple[str | None, str | None, str | None, str | None]:
    resolved_jd_id = _normalize_optional_text(jd_id, "jd_id")
    resolved_resume_version_id = _normalize_optional_text(
        resume_version_id,
        "resume_version_id",
    )
    resolved_match_report_id = _normalize_optional_text(
        match_report_id,
        "match_report_id",
    )
    resolved_agent_run_id = _normalize_optional_text(agent_run_id, "agent_run_id")

    match_report: MatchReportModel | None = None
    if resolved_match_report_id:
        match_report = db.get(MatchReportModel, resolved_match_report_id)
        if not match_report:
            raise AppError(
                code="match_report_not_found",
                message="Match report was not found.",
                status_code=404,
                details={"match_report_id": resolved_match_report_id},
            )
        if resolved_jd_id and match_report.jd_id != resolved_jd_id:
            raise _invalid_field(
                "match_report_id",
                "match_report_id does not belong to the given jd_id.",
            )
        if (
            resolved_resume_version_id
            and match_report.resume_version_id != resolved_resume_version_id
        ):
            raise _invalid_field(
                "match_report_id",
                "match_report_id does not belong to the given resume_version_id.",
            )
        resolved_jd_id = resolved_jd_id or match_report.jd_id
        resolved_resume_version_id = (
            resolved_resume_version_id or match_report.resume_version_id
        )

    if resolved_jd_id:
        job = db.get(JobDescription, resolved_jd_id)
        if not job or job.status != "active":
            raise AppError(
                code="job_not_found",
                message="JD was not found.",
                status_code=404,
                details={"jd_id": resolved_jd_id},
            )
    if resolved_resume_version_id:
        version = db.get(ResumeVersion, resolved_resume_version_id)
        if not version:
            raise AppError(
                code="resume_version_not_found",
                message="Resume version was not found.",
                status_code=404,
                details={"resume_version_id": resolved_resume_version_id},
            )
    if resolved_agent_run_id:
        agent_run = db.get(AgentRun, resolved_agent_run_id)
        if not agent_run:
            raise AppError(
                code="agent_run_not_found",
                message="Agent run was not found.",
                status_code=404,
                details={"agent_run_id": resolved_agent_run_id},
            )

    return (
        resolved_jd_id,
        resolved_resume_version_id,
        resolved_match_report_id,
        resolved_agent_run_id,
    )


def create_application(
    db: Session,
    payload: ApplicationCreateRequest,
) -> ApplicationRecord:
    jd_id, resume_version_id, match_report_id, agent_run_id = _validate_and_resolve_refs(
        db,
        jd_id=payload.jd_id,
        resume_version_id=payload.resume_version_id,
        match_report_id=payload.match_report_id,
        agent_run_id=payload.agent_run_id,
    )
    role_category = _normalize_optional_text(payload.role_category, "role_category")
    if role_category is None:
        role_category = _latest_job_profile_role_category(db, jd_id)

    return application_repository.create_application(
        db,
        company=_normalize_required_text(payload.company, "company"),
        role_title=_normalize_required_text(payload.role_title, "role_title"),
        role_category=role_category,
        jd_id=jd_id,
        resume_version_id=resume_version_id,
        match_report_id=match_report_id,
        agent_run_id=agent_run_id,
        status=_normalize_status(payload.status),
        apply_date=payload.apply_date,
        next_step_date=payload.next_step_date,
        interview_notes=_normalize_optional_text(payload.interview_notes, "interview_notes"),
        reflection=_normalize_optional_text(payload.reflection, "reflection"),
        tags=_normalize_tags(payload.tags),
    )


def list_applications(
    db: Session,
    *,
    status: str | None = None,
    company: str | None = None,
    role_category: str | None = None,
    resume_version_id: str | None = None,
    jd_id: str | None = None,
    agent_run_id: str | None = None,
) -> list[ApplicationRecord]:
    normalized_status = _normalize_status(status) if status else None
    return application_repository.list_applications(
        db,
        status=normalized_status,
        company=_normalize_optional_text(company, "company"),
        role_category=_normalize_optional_text(role_category, "role_category"),
        resume_version_id=_normalize_optional_text(
            resume_version_id,
            "resume_version_id",
        ),
        jd_id=_normalize_optional_text(jd_id, "jd_id"),
        agent_run_id=_normalize_optional_text(agent_run_id, "agent_run_id"),
    )


def get_application(db: Session, application_id: str) -> ApplicationRecord:
    return application_repository.get_application(db, application_id)


def update_application(
    db: Session,
    application_id: str,
    payload: ApplicationUpdateRequest,
) -> ApplicationRecord:
    application = application_repository.get_application_model(db, application_id)
    if not application:
        raise AppError(
            code="application_not_found",
            message="Application was not found.",
            status_code=404,
            details={"application_id": application_id},
        )

    update_data: dict[str, Any] = payload.model_dump(exclude_unset=True)
    jd_id = update_data.get("jd_id", application.jd_id)
    resume_version_id = update_data.get(
        "resume_version_id",
        application.resume_version_id,
    )
    match_report_id = update_data.get(
        "match_report_id",
        application.match_report_id,
    )
    agent_run_id = update_data.get("agent_run_id", application.agent_run_id)
    (
        resolved_jd_id,
        resolved_resume_version_id,
        resolved_match_report_id,
        resolved_agent_run_id,
    ) = (
        _validate_and_resolve_refs(
            db,
            jd_id=jd_id,
            resume_version_id=resume_version_id,
            match_report_id=match_report_id,
            agent_run_id=agent_run_id,
        )
    )

    normalized_role_category = None
    clear_role_category = False
    if "role_category" in update_data:
        normalized_role_category = _normalize_optional_text(
            update_data["role_category"],
            "role_category",
        )
        clear_role_category = normalized_role_category is None
    elif application.role_category is None:
        normalized_role_category = _latest_job_profile_role_category(db, resolved_jd_id)

    return application_repository.update_application(
        db,
        application,
        company=_normalize_required_text(update_data["company"], "company")
        if "company" in update_data and update_data["company"] is not None
        else None,
        role_title=_normalize_required_text(update_data["role_title"], "role_title")
        if "role_title" in update_data and update_data["role_title"] is not None
        else None,
        role_category=normalized_role_category,
        clear_role_category=clear_role_category,
        jd_id=resolved_jd_id,
        clear_jd_id=("jd_id" in update_data and update_data["jd_id"] is None),
        resume_version_id=resolved_resume_version_id,
        clear_resume_version_id=(
            "resume_version_id" in update_data
            and update_data["resume_version_id"] is None
        ),
        match_report_id=resolved_match_report_id,
        clear_match_report_id=(
            "match_report_id" in update_data
            and update_data["match_report_id"] is None
        ),
        agent_run_id=resolved_agent_run_id,
        clear_agent_run_id=(
            "agent_run_id" in update_data and update_data["agent_run_id"] is None
        ),
        status=_normalize_status(update_data["status"])
        if "status" in update_data and update_data["status"] is not None
        else None,
        apply_date=update_data.get("apply_date"),
        clear_apply_date=("apply_date" in update_data and update_data["apply_date"] is None),
        next_step_date=update_data.get("next_step_date"),
        clear_next_step_date=(
            "next_step_date" in update_data and update_data["next_step_date"] is None
        ),
        interview_notes=_normalize_optional_text(
            update_data.get("interview_notes"),
            "interview_notes",
        )
        if "interview_notes" in update_data
        else None,
        clear_interview_notes=(
            "interview_notes" in update_data
            and _normalize_optional_text(update_data["interview_notes"], "interview_notes")
            is None
        ),
        reflection=_normalize_optional_text(update_data.get("reflection"), "reflection")
        if "reflection" in update_data
        else None,
        clear_reflection=(
            "reflection" in update_data
            and _normalize_optional_text(update_data["reflection"], "reflection") is None
        ),
        tags=_normalize_tags(update_data["tags"])
        if "tags" in update_data and update_data["tags"] is not None
        else None,
    )


def get_application_stats(db: Session) -> ApplicationStats:
    applications = application_repository.list_applications(db)
    by_status = {status: 0 for status in sorted(APPLICATION_STATUSES)}
    for application in applications:
        by_status[application.status] = by_status.get(application.status, 0) + 1

    return ApplicationStats(
        total_applications=len(applications),
        by_status=by_status,
        interview_count=sum(by_status.get(status, 0) for status in INTERVIEW_STATUSES),
        offer_count=by_status.get("offer", 0),
        rejected_count=by_status.get("rejected", 0),
        active_count=sum(
            count for status, count in by_status.items() if status not in INACTIVE_STATUSES
        ),
    )
