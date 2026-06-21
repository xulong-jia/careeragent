from sqlalchemy.orm import Session

from app.agents import runner, state
from app.agents.workflows import get_workflow_definition
from app.core.errors import AppError
from app.models.agent import AgentRun


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
