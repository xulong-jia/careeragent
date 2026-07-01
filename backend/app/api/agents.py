from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.logging import log_event
from app.core.metrics import record_domain_event
from app.db.session import get_db
from app.schemas.agents import (
    AgentRunCreateRequest,
    AgentRunCreateResponse,
    AgentRunDetailResponse,
    AgentRunRecord,
    AgentRunResumeRequest,
    AgentStepListResponse,
)
from app.schemas.common import ApiResponse, ListResponse
from app.services import agent_service


router = APIRouter(prefix="/api/agents/runs", tags=["agents"])


@router.post(
    "",
    response_model=ApiResponse[AgentRunCreateResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_agent_run(
    request: Request,
    payload: AgentRunCreateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    run = agent_service.create_run_for_workflow(db, payload.model_dump())
    steps_count = agent_service.count_steps_for_run(db, run.id)
    data = AgentRunCreateResponse(
        run=AgentRunRecord.model_validate(run),
        steps_count=steps_count,
    )
    record_domain_event("agent.run.created")
    log_event(
        "agent_run_created",
        request_id=request.state.request_id,
        run_id=run.id,
        workflow_name=run.workflow_name,
        status=run.status,
        steps_count=steps_count,
    )
    return {"data": data, "request_id": request.state.request_id}


@router.post(
    "/{run_id}/resume",
    response_model=ApiResponse[AgentRunCreateResponse],
)
async def resume_agent_run(
    request: Request,
    run_id: str,
    payload: AgentRunResumeRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    run = agent_service.resume_run(
        db,
        run_id,
        payload.model_dump(exclude_none=True),
    )
    steps_count = agent_service.count_steps_for_run(db, run.id)
    data = AgentRunCreateResponse(
        run=AgentRunRecord.model_validate(run),
        steps_count=steps_count,
    )
    record_domain_event("agent.run.resumed")
    log_event(
        "agent_run_resumed",
        request_id=request.state.request_id,
        run_id=run.id,
        workflow_name=run.workflow_name,
        status=run.status,
        steps_count=steps_count,
    )
    return {"data": data, "request_id": request.state.request_id}


@router.post(
    "/{run_id}/retry",
    response_model=ApiResponse[AgentRunCreateResponse],
)
async def retry_agent_run(
    request: Request,
    run_id: str,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    run = agent_service.retry_run(db, run_id)
    steps_count = agent_service.count_steps_for_run(db, run.id)
    data = AgentRunCreateResponse(
        run=AgentRunRecord.model_validate(run),
        steps_count=steps_count,
    )
    record_domain_event("agent.run.retried")
    log_event(
        "agent_run_retried",
        request_id=request.state.request_id,
        run_id=run.id,
        workflow_name=run.workflow_name,
        status=run.status,
        retry_attempt=run.retry_attempt,
        steps_count=steps_count,
    )
    return {"data": data, "request_id": request.state.request_id}


@router.post(
    "/{run_id}/cancel",
    response_model=ApiResponse[AgentRunCreateResponse],
)
async def cancel_agent_run(
    request: Request,
    run_id: str,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    run = agent_service.cancel_run(db, run_id)
    steps_count = agent_service.count_steps_for_run(db, run.id)
    data = AgentRunCreateResponse(
        run=AgentRunRecord.model_validate(run),
        steps_count=steps_count,
    )
    record_domain_event("agent.run.cancelled")
    log_event(
        "agent_run_cancelled",
        request_id=request.state.request_id,
        run_id=run.id,
        workflow_name=run.workflow_name,
        status=run.status,
        steps_count=steps_count,
    )
    return {"data": data, "request_id": request.state.request_id}


@router.get("", response_model=ApiResponse[ListResponse[AgentRunRecord]])
async def list_agent_runs(
    request: Request,
    workflow_name: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    runs = agent_service.list_runs(
        db,
        workflow_name=workflow_name,
        status=status,
        limit=limit,
    )
    return {
        "data": ListResponse(items=runs, total=len(runs)),
        "request_id": request.state.request_id,
    }


@router.get("/{run_id}", response_model=ApiResponse[AgentRunDetailResponse])
async def get_agent_run(
    request: Request,
    run_id: str,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    run = agent_service.get_run(db, run_id)
    steps_count = len(agent_service.list_steps_for_run(db, run_id))
    data = AgentRunDetailResponse(run=run, steps_count=steps_count)
    return {"data": data, "request_id": request.state.request_id}


@router.get("/{run_id}/steps", response_model=ApiResponse[AgentStepListResponse])
async def list_agent_run_steps(
    request: Request,
    run_id: str,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    steps = agent_service.list_steps_for_run(db, run_id)
    data = AgentStepListResponse(steps=steps, total=len(steps))
    return {"data": data, "request_id": request.state.request_id}
