from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.tenant import (
    current_user_id,
    current_workspace_id,
    is_owned,
    owner_filter,
    require_owned,
)
from app.models.project import Project, ProjectRewrite
from app.schemas.projects import ProjectRecord, ProjectRewriteRecord


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


def _next_project_rewrite_id(db: Session) -> str:
    for _ in range(10):
        rewrite_id = f"project_rewrite_{uuid4().hex[:12]}"
        if db.get(ProjectRewrite, rewrite_id) is None:
            return rewrite_id
    raise AppError(
        code="project_rewrite_id_generation_failed",
        message="Unable to generate a unique project rewrite id.",
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


def _to_project_rewrite_record(record: ProjectRewrite) -> ProjectRewriteRecord:
    return ProjectRewriteRecord(
        id=record.id,
        project_id=record.project_id,
        jd_id=record.jd_id,
        resume_version_id=record.resume_version_id,
        match_report_id=record.match_report_id,
        profile_id=record.profile_id,
        matched_points=list(record.matched_points or []),
        missing_points=list(record.missing_points or []),
        evidence_required=list(record.evidence_required or []),
        rewritten_bullets=list(record.rewritten_bullets or []),
        forbidden_changes=list(record.forbidden_changes or []),
        risk_flags=list(record.risk_flags or []),
        rewrite_strategy=record.rewrite_strategy,
        created_at=record.created_at,
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
        user_id=current_user_id(),
        workspace_id=current_workspace_id(),
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


def create_project_rewrite(
    db: Session,
    *,
    project_id: str,
    jd_id: str,
    resume_version_id: str | None,
    match_report_id: str | None,
    profile_id: str | None,
    matched_points: list[dict[str, object]],
    missing_points: list[dict[str, object]],
    evidence_required: list[dict[str, object]],
    rewritten_bullets: list[dict[str, object]],
    forbidden_changes: list[str],
    risk_flags: list[dict[str, object]],
    rewrite_strategy: str,
) -> ProjectRewriteRecord:
    record = ProjectRewrite(
        id=_next_project_rewrite_id(db),
        user_id=current_user_id(),
        workspace_id=current_workspace_id(),
        project_id=project_id,
        jd_id=jd_id,
        resume_version_id=resume_version_id,
        match_report_id=match_report_id,
        profile_id=profile_id,
        matched_points=matched_points,
        missing_points=missing_points,
        evidence_required=evidence_required,
        rewritten_bullets=rewritten_bullets,
        forbidden_changes=forbidden_changes,
        risk_flags=risk_flags,
        rewrite_strategy=rewrite_strategy,
    )
    try:
        db.add(record)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(record)
    return _to_project_rewrite_record(record)


def list_projects(
    db: Session,
    *,
    profile_id: str | None = None,
    resume_version_id: str | None = None,
    status: str | None = None,
) -> list[ProjectRecord]:
    statement = select(Project).where(*owner_filter(Project))
    if profile_id is not None:
        statement = statement.where(Project.profile_id == profile_id)
    if resume_version_id is not None:
        statement = statement.where(Project.resume_version_id == resume_version_id)
    if status is not None:
        statement = statement.where(Project.status == status)
    projects = db.scalars(statement.order_by(Project.created_at, Project.id)).all()
    return [_to_project_record(project) for project in projects]


def get_project_model(db: Session, project_id: str) -> Project | None:
    project = db.get(Project, project_id)
    return project if project and is_owned(project) else None


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


def get_project_rewrite(db: Session, rewrite_id: str) -> ProjectRewriteRecord:
    record = db.get(ProjectRewrite, rewrite_id)
    require_owned(
        record,
        code="project_rewrite_not_found",
        message="Project rewrite was not found.",
        details={"rewrite_id": rewrite_id},
    )
    if not record:
        raise AppError(
            code="project_rewrite_not_found",
            message="Project rewrite was not found.",
            status_code=404,
            details={"rewrite_id": rewrite_id},
        )
    return _to_project_rewrite_record(record)


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
