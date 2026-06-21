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
    run = agent_repository.get_run(db, run_id)
    if not run:
        raise AppError(
            code="agent_run_not_found",
            message="Agent run was not found.",
            status_code=404,
            details={"run_id": run_id},
        )
    return run


def list_steps_for_run(db: Session, run_id: str) -> list[AgentStepRecord]:
    get_run(db, run_id)
    return agent_repository.list_steps_for_run(db, run_id)


def count_steps_for_run(db: Session, run_id: str) -> int:
    return len(agent_repository.list_steps_for_run(db, run_id))
