from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.tenant import current_user_id, current_workspace_id, is_owned, owner_filter
from app.models.agent import AgentRun, AgentStep
from app.schemas.agents import AgentRunRecord, AgentStepRecord


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _duration_ms(started_at: datetime | None, finished_at: datetime) -> int | None:
    if not started_at:
        return None
    return round((finished_at - started_at).total_seconds() * 1000)


def _next_run_id(db: Session) -> str:
    count = db.scalar(select(func.count()).select_from(AgentRun)) or 0
    return f"agent_run_{count + 1:04d}"


def _next_step_id(run_id: str, step_order: int) -> str:
    return f"{run_id}_step_{step_order:04d}"


def _to_run_record(run: AgentRun) -> AgentRunRecord:
    return AgentRunRecord.model_validate(run)


def _to_step_record(step: AgentStep) -> AgentStepRecord:
    return AgentStepRecord.model_validate(step)


def create_run(
    db: Session,
    *,
    workflow_name: str,
    input_refs: dict[str, object],
) -> AgentRun:
    run = AgentRun(
        id=_next_run_id(db),
        user_id=current_user_id(),
        workspace_id=current_workspace_id(),
        workflow_name=workflow_name,
        input_refs=input_refs,
        output_refs={},
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def get_run_model(db: Session, run_id: str) -> AgentRun | None:
    run = db.get(AgentRun, run_id)
    return run if run and is_owned(run) else None


def get_run(db: Session, run_id: str) -> AgentRunRecord | None:
    run = get_run_model(db, run_id)
    return _to_run_record(run) if run else None


def list_runs(
    db: Session,
    *,
    workflow_name: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[AgentRunRecord]:
    statement = select(AgentRun).where(*owner_filter(AgentRun))
    if workflow_name:
        statement = statement.where(AgentRun.workflow_name == workflow_name)
    if status:
        statement = statement.where(AgentRun.status == status)
    statement = statement.order_by(desc(AgentRun.created_at), desc(AgentRun.id)).limit(limit)
    runs = db.scalars(statement).all()
    return [_to_run_record(run) for run in runs]


def create_step(
    db: Session,
    *,
    run_id: str,
    step_name: str,
    step_order: int,
    input_refs: dict[str, object],
) -> AgentStep:
    step = AgentStep(
        id=_next_step_id(run_id, step_order),
        run_id=run_id,
        step_name=step_name,
        step_order=step_order,
        input_refs=input_refs,
        output_refs={},
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


def update_run_status(
    db: Session,
    run: AgentRun,
    *,
    status: str,
) -> AgentRun:
    now = _now()
    run.status = status
    if status == "running" and run.started_at is None:
        run.started_at = now
    if status in {"completed", "failed", "need_more_info"}:
        run.finished_at = now
        run.duration_ms = _duration_ms(run.started_at, now)
    db.commit()
    db.refresh(run)
    return run


def update_run_outputs(
    db: Session,
    run: AgentRun,
    *,
    output_refs: dict[str, object],
) -> AgentRun:
    run.output_refs = output_refs
    db.commit()
    db.refresh(run)
    return run


def update_run_need_more_info(
    db: Session,
    run: AgentRun,
    *,
    missing_slots: list[dict[str, object]],
    questions: list[dict[str, object]],
    output_refs: dict[str, object] | None = None,
) -> AgentRun:
    run.status = "need_more_info"
    run.missing_slots = missing_slots
    run.questions = questions
    if output_refs is not None:
        run.output_refs = output_refs
    now = _now()
    run.finished_at = now
    run.duration_ms = _duration_ms(run.started_at, now)
    db.commit()
    db.refresh(run)
    return run


def update_run_error(
    db: Session,
    run: AgentRun,
    *,
    error_code: str,
    error_message: str,
) -> AgentRun:
    run.status = "failed"
    run.error_code = error_code
    run.error_message = error_message
    now = _now()
    run.finished_at = now
    run.duration_ms = _duration_ms(run.started_at, now)
    db.commit()
    db.refresh(run)
    return run


def update_step_status(
    db: Session,
    step: AgentStep,
    *,
    status: str,
) -> AgentStep:
    now = _now()
    step.status = status
    if status == "running" and step.started_at is None:
        step.started_at = now
    if status in {"completed", "failed", "skipped", "need_more_info"}:
        step.finished_at = now
        step.duration_ms = _duration_ms(step.started_at, now)
    db.commit()
    db.refresh(step)
    return step


def update_step_outputs(
    db: Session,
    step: AgentStep,
    *,
    status: str,
    output_refs: dict[str, object],
) -> AgentStep:
    now = _now()
    step.status = status
    step.output_refs = output_refs
    step.finished_at = now
    step.duration_ms = _duration_ms(step.started_at, now)
    db.commit()
    db.refresh(step)
    return step


def update_step_error(
    db: Session,
    step: AgentStep,
    *,
    error_code: str,
    error_message: str,
) -> AgentStep:
    now = _now()
    step.status = "failed"
    step.error_code = error_code
    step.error_message = error_message
    step.finished_at = now
    step.duration_ms = _duration_ms(step.started_at, now)
    db.commit()
    db.refresh(step)
    return step


def list_steps_for_run(db: Session, run_id: str) -> list[AgentStepRecord]:
    run = get_run_model(db, run_id)
    if not run:
        return []
    steps = db.scalars(
        select(AgentStep)
        .where(AgentStep.run_id == run_id)
        .order_by(AgentStep.step_order)
    ).all()
    return [_to_step_record(step) for step in steps]
