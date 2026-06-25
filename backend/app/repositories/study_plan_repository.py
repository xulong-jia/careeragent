from uuid import uuid4

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
    )
    try:
        db.add(plan)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(plan)
    return _to_study_plan_record(plan)
