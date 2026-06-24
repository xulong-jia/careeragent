from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.application import Application
from app.schemas.applications import ApplicationRecord


def _next_application_id(db: Session) -> str:
    count = db.scalar(select(func.count()).select_from(Application)) or 0
    return f"application_{count + 1:04d}"


def _to_application_record(application: Application) -> ApplicationRecord:
    return ApplicationRecord(
        application_id=application.id,
        user_id=application.user_id,
        company=application.company,
        role_title=application.role_title,
        role_category=application.role_category,
        jd_id=application.jd_id,
        resume_version_id=application.resume_version_id,
        match_report_id=application.match_report_id,
        status=application.status,
        apply_date=application.apply_date,
        next_step_date=application.next_step_date,
        interview_notes=application.interview_notes,
        reflection=application.reflection,
        tags=list(application.tags or []),
        created_at=application.created_at,
        updated_at=application.updated_at,
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
    status: str,
    apply_date,
    next_step_date,
    interview_notes: str | None,
    reflection: str | None,
    tags: list[str],
) -> ApplicationRecord:
    application = Application(
        id=_next_application_id(db),
        user_id="default",
        company=company,
        role_title=role_title,
        role_category=role_category,
        jd_id=jd_id,
        resume_version_id=resume_version_id,
        match_report_id=match_report_id,
        status=status,
        apply_date=apply_date,
        next_step_date=next_step_date,
        interview_notes=interview_notes,
        reflection=reflection,
        tags=tags,
    )
    try:
        db.add(application)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(application)
    return _to_application_record(application)


def list_applications(
    db: Session,
    *,
    status: str | None = None,
    company: str | None = None,
    role_category: str | None = None,
    resume_version_id: str | None = None,
    jd_id: str | None = None,
) -> list[ApplicationRecord]:
    statement = select(Application).order_by(Application.created_at, Application.id)
    if status:
        statement = statement.where(Application.status == status)
    if company:
        statement = statement.where(Application.company.ilike(f"%{company}%"))
    if role_category:
        statement = statement.where(Application.role_category == role_category)
    if resume_version_id:
        statement = statement.where(Application.resume_version_id == resume_version_id)
    if jd_id:
        statement = statement.where(Application.jd_id == jd_id)

    applications = db.scalars(statement).all()
    return [_to_application_record(application) for application in applications]


def get_application_model(db: Session, application_id: str) -> Application | None:
    return db.get(Application, application_id)


def get_application(db: Session, application_id: str) -> ApplicationRecord:
    application = get_application_model(db, application_id)
    if not application:
        raise AppError(
            code="application_not_found",
            message="Application was not found.",
            status_code=404,
            details={"application_id": application_id},
        )
    return _to_application_record(application)


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
    status: str | None = None,
    apply_date=None,
    clear_apply_date: bool = False,
    next_step_date=None,
    clear_next_step_date: bool = False,
    interview_notes: str | None = None,
    clear_interview_notes: bool = False,
    reflection: str | None = None,
    clear_reflection: bool = False,
    tags: list[str] | None = None,
) -> ApplicationRecord:
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
    if clear_interview_notes:
        application.interview_notes = None
    elif interview_notes is not None:
        application.interview_notes = interview_notes
    if clear_reflection:
        application.reflection = None
    elif reflection is not None:
        application.reflection = reflection
    if tags is not None:
        application.tags = tags

    try:
        db.add(application)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(application)
    return _to_application_record(application)
