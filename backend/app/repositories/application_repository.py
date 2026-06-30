from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.application import Application, ApplicationStatusHistory
from app.schemas.applications import ApplicationRecord, ApplicationStatusHistoryRecord


def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _next_application_id(db: Session) -> str:
    for _ in range(10):
        application_id = f"app_{uuid4().hex[:12]}"
        if db.get(Application, application_id) is None:
            return application_id
    raise AppError(
        code="application_id_generation_failed",
        message="Unable to generate a unique application id.",
        status_code=500,
        details={},
    )


def _next_status_history_id(db: Session) -> str:
    for _ in range(10):
        history_id = f"app_hist_{uuid4().hex[:12]}"
        if db.get(ApplicationStatusHistory, history_id) is None:
            return history_id
    raise AppError(
        code="application_status_history_id_generation_failed",
        message="Unable to generate a unique application status history id.",
        status_code=500,
        details={},
    )


def _to_status_history_record(
    history: ApplicationStatusHistory,
) -> ApplicationStatusHistoryRecord:
    return ApplicationStatusHistoryRecord(
        history_id=history.id,
        application_id=history.application_id,
        from_status=history.from_status,
        to_status=history.to_status,
        changed_at=history.changed_at,
        reason=history.reason,
        note=history.note,
        created_at=history.created_at,
    )


def _to_application_record(
    application: Application,
    *,
    status_history: list[ApplicationStatusHistoryRecord] | None = None,
) -> ApplicationRecord:
    return ApplicationRecord(
        application_id=application.id,
        user_id=application.user_id,
        company=application.company,
        role_title=application.role_title,
        role_category=application.role_category,
        jd_id=application.jd_id,
        resume_version_id=application.resume_version_id,
        match_report_id=application.match_report_id,
        agent_run_id=application.agent_run_id,
        status=application.status,
        apply_date=application.apply_date,
        next_step_date=application.next_step_date,
        source_url=application.source_url,
        location=application.location,
        priority=application.priority,
        notes=application.notes,
        interview_notes=application.interview_notes,
        reflection=application.reflection,
        interview_question_ids=list(application.interview_question_ids or []),
        last_contact_date=application.last_contact_date,
        tags=list(application.tags or []),
        status_history=status_history or [],
        created_at=application.created_at,
        updated_at=application.updated_at,
    )


def _build_status_history(
    db: Session,
    *,
    application_id: str,
    from_status: str | None,
    to_status: str,
    reason: str | None = None,
    note: str | None = None,
) -> ApplicationStatusHistory:
    return ApplicationStatusHistory(
        id=_next_status_history_id(db),
        application_id=application_id,
        from_status=from_status,
        to_status=to_status,
        changed_at=_now_utc(),
        reason=reason,
        note=note,
    )


def create_application(
    db: Session,
    *,
    company: str,
    role_title: str,
    role_category: str | None,
    jd_id: str | None,
    resume_version_id: str | None,
    match_report_id: str | None,
    agent_run_id: str | None,
    status: str,
    apply_date,
    next_step_date,
    source_url: str | None,
    location: str | None,
    priority: str,
    notes: str | None,
    interview_notes: str | None,
    reflection: str | None,
    interview_question_ids: list[str],
    last_contact_date,
    tags: list[str],
) -> ApplicationRecord:
    application_id = _next_application_id(db)
    application = Application(
        id=application_id,
        user_id="default",
        company=company,
        role_title=role_title,
        role_category=role_category,
        jd_id=jd_id,
        resume_version_id=resume_version_id,
        match_report_id=match_report_id,
        agent_run_id=agent_run_id,
        status=status,
        apply_date=apply_date,
        next_step_date=next_step_date,
        source_url=source_url,
        location=location,
        priority=priority,
        notes=notes,
        interview_notes=interview_notes,
        reflection=reflection,
        interview_question_ids=interview_question_ids,
        last_contact_date=last_contact_date,
        tags=tags,
    )
    history = _build_status_history(
        db,
        application_id=application_id,
        from_status=None,
        to_status=status,
        reason="created",
        note="Initial application status.",
    )
    try:
        db.add(application)
        db.add(history)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(application)
    db.refresh(history)
    return _to_application_record(
        application,
        status_history=[_to_status_history_record(history)],
    )


def list_applications(
    db: Session,
    *,
    status: str | None = None,
    company: str | None = None,
    role_category: str | None = None,
    resume_version_id: str | None = None,
    jd_id: str | None = None,
    match_report_id: str | None = None,
    agent_run_id: str | None = None,
    priority: str | None = None,
    apply_date_from=None,
    apply_date_to=None,
    next_step_date_from=None,
    next_step_date_to=None,
) -> list[ApplicationRecord]:
    statement = select(Application).order_by(Application.created_at, Application.id)
    if status:
        statement = statement.where(Application.status == status)
    else:
        statement = statement.where(Application.status != "archived")
    if company:
        statement = statement.where(Application.company.ilike(f"%{company}%"))
    if role_category:
        statement = statement.where(Application.role_category == role_category)
    if resume_version_id:
        statement = statement.where(Application.resume_version_id == resume_version_id)
    if jd_id:
        statement = statement.where(Application.jd_id == jd_id)
    if match_report_id:
        statement = statement.where(Application.match_report_id == match_report_id)
    if agent_run_id:
        statement = statement.where(Application.agent_run_id == agent_run_id)
    if priority:
        statement = statement.where(Application.priority == priority)
    if apply_date_from:
        statement = statement.where(Application.apply_date >= apply_date_from)
    if apply_date_to:
        statement = statement.where(Application.apply_date <= apply_date_to)
    if next_step_date_from:
        statement = statement.where(Application.next_step_date >= next_step_date_from)
    if next_step_date_to:
        statement = statement.where(Application.next_step_date <= next_step_date_to)

    applications = db.scalars(statement).all()
    return [_to_application_record(application) for application in applications]


def get_application_model(db: Session, application_id: str) -> Application | None:
    return db.get(Application, application_id)


def list_status_history(
    db: Session,
    application_id: str,
) -> list[ApplicationStatusHistoryRecord]:
    statement = (
        select(ApplicationStatusHistory)
        .where(ApplicationStatusHistory.application_id == application_id)
        .order_by(
            ApplicationStatusHistory.changed_at,
            ApplicationStatusHistory.created_at,
            ApplicationStatusHistory.id,
        )
    )
    return [_to_status_history_record(history) for history in db.scalars(statement).all()]


def get_application(db: Session, application_id: str) -> ApplicationRecord:
    application = get_application_model(db, application_id)
    if not application:
        raise AppError(
            code="application_not_found",
            message="Application was not found.",
            status_code=404,
            details={"application_id": application_id},
        )
    return _to_application_record(
        application,
        status_history=list_status_history(db, application_id),
    )


def update_application(
    db: Session,
    application: Application,
    *,
    company: str | None = None,
    role_title: str | None = None,
    role_category: str | None = None,
    clear_role_category: bool = False,
    jd_id: str | None = None,
    clear_jd_id: bool = False,
    resume_version_id: str | None = None,
    clear_resume_version_id: bool = False,
    match_report_id: str | None = None,
    clear_match_report_id: bool = False,
    agent_run_id: str | None = None,
    clear_agent_run_id: bool = False,
    status: str | None = None,
    status_reason: str | None = None,
    status_note: str | None = None,
    apply_date=None,
    clear_apply_date: bool = False,
    next_step_date=None,
    clear_next_step_date: bool = False,
    source_url: str | None = None,
    clear_source_url: bool = False,
    location: str | None = None,
    clear_location: bool = False,
    priority: str | None = None,
    notes: str | None = None,
    clear_notes: bool = False,
    interview_notes: str | None = None,
    clear_interview_notes: bool = False,
    reflection: str | None = None,
    clear_reflection: bool = False,
    interview_question_ids: list[str] | None = None,
    last_contact_date=None,
    clear_last_contact_date: bool = False,
    tags: list[str] | None = None,
) -> ApplicationRecord:
    previous_status = application.status
    if company is not None:
        application.company = company
    if role_title is not None:
        application.role_title = role_title
    if clear_role_category:
        application.role_category = None
    elif role_category is not None:
        application.role_category = role_category
    if clear_jd_id:
        application.jd_id = None
    elif jd_id is not None:
        application.jd_id = jd_id
    if clear_resume_version_id:
        application.resume_version_id = None
    elif resume_version_id is not None:
        application.resume_version_id = resume_version_id
    if clear_match_report_id:
        application.match_report_id = None
    elif match_report_id is not None:
        application.match_report_id = match_report_id
    if clear_agent_run_id:
        application.agent_run_id = None
    elif agent_run_id is not None:
        application.agent_run_id = agent_run_id
    if status is not None:
        application.status = status
    if clear_apply_date:
        application.apply_date = None
    elif apply_date is not None:
        application.apply_date = apply_date
    if clear_next_step_date:
        application.next_step_date = None
    elif next_step_date is not None:
        application.next_step_date = next_step_date
    if clear_source_url:
        application.source_url = None
    elif source_url is not None:
        application.source_url = source_url
    if clear_location:
        application.location = None
    elif location is not None:
        application.location = location
    if priority is not None:
        application.priority = priority
    if clear_notes:
        application.notes = None
    elif notes is not None:
        application.notes = notes
    if clear_interview_notes:
        application.interview_notes = None
    elif interview_notes is not None:
        application.interview_notes = interview_notes
    if clear_reflection:
        application.reflection = None
    elif reflection is not None:
        application.reflection = reflection
    if interview_question_ids is not None:
        application.interview_question_ids = interview_question_ids
    if clear_last_contact_date:
        application.last_contact_date = None
    elif last_contact_date is not None:
        application.last_contact_date = last_contact_date
    if tags is not None:
        application.tags = tags

    history: ApplicationStatusHistory | None = None
    if status is not None and status != previous_status:
        history = _build_status_history(
            db,
            application_id=application.id,
            from_status=previous_status,
            to_status=status,
            reason=status_reason,
            note=status_note,
        )

    try:
        db.add(application)
        if history:
            db.add(history)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(application)
    if history:
        db.refresh(history)
    return _to_application_record(
        application,
        status_history=list_status_history(db, application.id),
    )


def archive_application(db: Session, application: Application) -> ApplicationRecord:
    return update_application(
        db,
        application,
        status="archived",
        status_reason="privacy_governance_delete",
        status_note="Archived through DELETE /api/applications/{application_id}.",
    )
