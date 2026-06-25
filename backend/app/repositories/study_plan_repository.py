from uuid import uuid4
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.study_plan import StudyPlan
from app.schemas.study_plans import StudyPlanRecord


def _next_study_plan_id(db: Session) -> str:
    for _ in range(10):
        plan_id = f"study_plan_{uuid4().hex[:12]}"
        if db.get(StudyPlan, plan_id) is None:
            return plan_id
    raise AppError(
        code="study_plan_id_generation_failed",
        message="Unable to generate a unique study plan id.",
        status_code=500,
        details={},
    )


def _to_study_plan_record(plan: StudyPlan) -> StudyPlanRecord:
    return StudyPlanRecord(
        id=plan.id,
        user_id=plan.user_id,
        match_report_id=plan.match_report_id,
        profile_id=plan.profile_id,
        project_rewrite_id=plan.project_rewrite_id,
        target_role=plan.target_role,
        source_refs=list(plan.source_refs or []),
        phases=list(plan.phases or []),
        status=plan.status,  # type: ignore[arg-type]
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


def create_study_plan(
    db: Session,
    *,
    match_report_id: str | None,
    profile_id: str | None,
    project_rewrite_id: str | None,
    target_role: str,
    source_refs: list[dict[str, str]],
    phases: list[dict[str, object]],
    status: str = "active",
) -> StudyPlanRecord:
    now = datetime.now(UTC)
    plan = StudyPlan(
        id=_next_study_plan_id(db),
        user_id="default",
        match_report_id=match_report_id,
        profile_id=profile_id,
        project_rewrite_id=project_rewrite_id,
        target_role=target_role,
        source_refs=source_refs,
        phases=phases,
        status=status,
        created_at=now,
        updated_at=now,
    )
    try:
        db.add(plan)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(plan)
    return _to_study_plan_record(plan)


def list_study_plans(
    db: Session,
    *,
    status: str | None = None,
    target_role: str | None = None,
    profile_id: str | None = None,
    match_report_id: str | None = None,
) -> list[StudyPlanRecord]:
    statement = select(StudyPlan)
    if status is not None:
        statement = statement.where(StudyPlan.status == status)
    if target_role is not None:
        statement = statement.where(StudyPlan.target_role == target_role)
    if profile_id is not None:
        statement = statement.where(StudyPlan.profile_id == profile_id)
    if match_report_id is not None:
        statement = statement.where(StudyPlan.match_report_id == match_report_id)
    plans = db.scalars(statement.order_by(StudyPlan.created_at, StudyPlan.id)).all()
    return [_to_study_plan_record(plan) for plan in plans]


def list_study_plan_models(db: Session) -> list[StudyPlan]:
    return db.scalars(select(StudyPlan).order_by(StudyPlan.created_at, StudyPlan.id)).all()


def get_study_plan_model(db: Session, study_plan_id: str) -> StudyPlan | None:
    return db.get(StudyPlan, study_plan_id)


def get_study_plan(db: Session, study_plan_id: str) -> StudyPlanRecord:
    plan = get_study_plan_model(db, study_plan_id)
    if not plan:
        raise AppError(
            code="study_plan_not_found",
            message="Study plan was not found.",
            status_code=404,
            details={"study_plan_id": study_plan_id},
        )
    return _to_study_plan_record(plan)


def update_study_plan_phases(
    db: Session,
    plan: StudyPlan,
    *,
    phases: list[dict[str, object]],
) -> StudyPlanRecord:
    plan.phases = phases
    plan.updated_at = datetime.now(UTC)
    try:
        db.add(plan)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(plan)
    return _to_study_plan_record(plan)
