from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.project import Project
from app.schemas.projects import ProjectRecord


def _next_project_id(db: Session) -> str:
    for _ in range(10):
        project_id = f"project_{uuid4().hex[:12]}"
        if db.get(Project, project_id) is None:
            return project_id
    raise AppError(
        code="project_id_generation_failed",
        message="Unable to generate a unique project id.",
        status_code=500,
        details={},
    )


def _to_project_record(project: Project) -> ProjectRecord:
    return ProjectRecord(
        id=project.id,
        user_id=project.user_id,
        profile_id=project.profile_id,
        resume_version_id=project.resume_version_id,
        name=project.name,
        role=project.role,
        period=project.period,
        background=project.background,
        tech_stack=list(project.tech_stack or []),
        responsibilities=list(project.responsibilities or []),
        results=list(project.results or []),
        evidence=list(project.evidence or []),
        status=project.status,  # type: ignore[arg-type]
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def create_project(
    db: Session,
    *,
    profile_id: str | None,
    resume_version_id: str | None,
    name: str,
    role: str | None,
    period: str | None,
    background: str | None,
    tech_stack: list[str],
    responsibilities: list[str],
    results: list[str],
    evidence: list[dict[str, object]],
    status: str,
) -> ProjectRecord:
    project = Project(
        id=_next_project_id(db),
        user_id="default",
        profile_id=profile_id,
        resume_version_id=resume_version_id,
        name=name,
        role=role,
        period=period,
        background=background,
        tech_stack=tech_stack,
        responsibilities=responsibilities,
        results=results,
        evidence=evidence,
        status=status,
    )
    try:
        db.add(project)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(project)
    return _to_project_record(project)


def list_projects(
    db: Session,
    *,
    profile_id: str | None = None,
    resume_version_id: str | None = None,
    status: str | None = None,
) -> list[ProjectRecord]:
    statement = select(Project)
    if profile_id is not None:
        statement = statement.where(Project.profile_id == profile_id)
    if resume_version_id is not None:
        statement = statement.where(Project.resume_version_id == resume_version_id)
    if status is not None:
        statement = statement.where(Project.status == status)
    projects = db.scalars(statement.order_by(Project.created_at, Project.id)).all()
    return [_to_project_record(project) for project in projects]


def get_project_model(db: Session, project_id: str) -> Project | None:
    return db.get(Project, project_id)


def get_project(db: Session, project_id: str) -> ProjectRecord:
    project = get_project_model(db, project_id)
    if not project:
        raise AppError(
            code="project_not_found",
            message="Project was not found.",
            status_code=404,
            details={"project_id": project_id},
        )
    return _to_project_record(project)


def update_project(
    db: Session,
    project: Project,
    *,
    updates: dict[str, object],
) -> ProjectRecord:
    for field_name, value in updates.items():
        setattr(project, field_name, value)

    try:
        db.add(project)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(project)
    return _to_project_record(project)
