from sqlalchemy.orm import Session

from app.agents import runner, state
from app.agents.workflows import get_workflow_definition
from app.core.errors import AppError
from app.models.agent import AgentRun
from app.repositories import agent_repository
from app.schemas.agents import AgentRunRecord, AgentStepRecord


def create_run_for_workflow(db: Session, payload: dict[str, object]) -> AgentRun:
    workflow_name = str(payload.get("workflow_name") or "").strip()
    workflow = get_workflow_definition(workflow_name)
    if not workflow:
        raise AppError(
            code=state.ERROR_AGENT_WORKFLOW_NOT_SUPPORTED,
            message="Agent workflow is not supported.",
            status_code=400,
            details={"workflow_name": workflow_name},
        )
    return runner.run_workflow(db, workflow=workflow, payload=payload)


def _get_run_model_or_404(db: Session, run_id: str) -> AgentRun:
    run = agent_repository.get_run_model(db, run_id)
    if not run:
        raise AppError(
            code="agent_run_not_found",
            message="Agent run was not found.",
            status_code=404,
            details={"run_id": run_id},
        )
    return run


def _workflow_for_run(run: AgentRun):
    workflow = get_workflow_definition(run.workflow_name)
    if not workflow:
        raise AppError(
            code=state.ERROR_AGENT_WORKFLOW_NOT_SUPPORTED,
            message="Agent workflow is not supported.",
            status_code=400,
            details={"workflow_name": run.workflow_name},
        )
    return workflow


def _payload_from_run(run: AgentRun, updates: dict[str, object] | None = None) -> dict[str, object]:
    payload = dict(run.input_refs or {})
    payload["workflow_name"] = run.workflow_name
    payload.pop("rag_query_present", None)
    for key, value in (updates or {}).items():
        if value is not None:
            payload[key] = value
    return payload


def resume_run(
    db: Session,
    run_id: str,
    payload: dict[str, object] | None = None,
) -> AgentRun:
    run = _get_run_model_or_404(db, run_id)
    if run.status != state.RUN_STATUS_NEED_MORE_INFO:
        raise AppError(
            code="agent_run_invalid_status",
            message="Only need_more_info agent runs can be resumed.",
            status_code=400,
            details={"run_id": run_id, "status": run.status},
        )
    workflow = _workflow_for_run(run)
    attempt = int(run.retry_attempt or 1) + 1
    return runner.run_workflow(
        db,
        workflow=workflow,
        payload=_payload_from_run(run, payload),
        existing_run=run,
        attempt=attempt,
        start_status=state.RUN_STATUS_RUNNING,
    )


def retry_run(db: Session, run_id: str) -> AgentRun:
    run = _get_run_model_or_404(db, run_id)
    if run.status != state.RUN_STATUS_FAILED:
        raise AppError(
            code="agent_run_invalid_status",
            message="Only failed agent runs can be retried.",
            status_code=400,
            details={"run_id": run_id, "status": run.status},
        )
    workflow = _workflow_for_run(run)
    attempt = int(run.retry_attempt or 1) + 1
    return runner.run_workflow(
        db,
        workflow=workflow,
        payload=_payload_from_run(run),
        existing_run=run,
        attempt=attempt,
        start_status=state.RUN_STATUS_RETRYING,
    )


def cancel_run(db: Session, run_id: str) -> AgentRun:
    run = _get_run_model_or_404(db, run_id)
    if run.status not in {
        state.RUN_STATUS_PENDING,
        state.RUN_STATUS_RUNNING,
        state.RUN_STATUS_NEED_MORE_INFO,
        state.RUN_STATUS_RETRYING,
    }:
        raise AppError(
            code="agent_run_invalid_status",
            message="Agent run cannot be cancelled from its current status.",
            status_code=400,
            details={"run_id": run_id, "status": run.status},
        )
    run.output_refs = {
        **(run.output_refs or {}),
        "cancelled": True,
        "cancel_reason": "cancel_requested",
    }
    return agent_repository.update_run_status(
        db,
        run,
        status=state.RUN_STATUS_CANCELLED,
    )


def list_runs(
    db: Session,
    *,
    workflow_name: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[AgentRunRecord]:
    bounded_limit = min(max(limit, 1), 100)
    return agent_repository.list_runs(
        db,
        workflow_name=workflow_name,
        status=status,
        limit=bounded_limit,
    )


def get_run(db: Session, run_id: str) -> AgentRunRecord:
    run = _get_run_model_or_404(db, run_id)
    return AgentRunRecord.model_validate(run)


def list_steps_for_run(db: Session, run_id: str) -> list[AgentStepRecord]:
    get_run(db, run_id)
    return agent_repository.list_steps_for_run(db, run_id)


def count_steps_for_run(db: Session, run_id: str) -> int:
    return len(agent_repository.list_steps_for_run(db, run_id))
