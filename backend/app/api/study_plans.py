from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse, ListResponse
from app.schemas.study_plans import (
    StudyPlanGenerateRequest,
    StudyPlanRecord,
    StudyPlanStatsResponse,
    StudyPlanStatus,
    StudyTaskStatusUpdateRequest,
)
from app.services import study_plan_service


router = APIRouter(prefix="/api/study-plans", tags=["study-plans"])


@router.post(
    "/generate",
    response_model=ApiResponse[StudyPlanRecord],
    status_code=status.HTTP_201_CREATED,
)
async def generate_study_plan(
    request: Request,
    payload: StudyPlanGenerateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    plan = study_plan_service.generate_study_plan(db, payload)
    return {"data": plan, "request_id": request.state.request_id}


@router.get("", response_model=ApiResponse[ListResponse[StudyPlanRecord]])
async def list_study_plans(
    request: Request,
    status: StudyPlanStatus | None = None,
    target_role: str | None = None,
    profile_id: str | None = None,
    match_report_id: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    plans = study_plan_service.list_study_plans(
        db,
        status=status,
        target_role=target_role,
        profile_id=profile_id,
        match_report_id=match_report_id,
    )
    return {
        "data": ListResponse(items=plans, total=len(plans)),
        "request_id": request.state.request_id,
    }


@router.get("/stats", response_model=ApiResponse[StudyPlanStatsResponse])
async def get_study_plan_stats(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    stats = study_plan_service.get_stats(db)
    return {"data": stats, "request_id": request.state.request_id}


@router.get("/{study_plan_id}", response_model=ApiResponse[StudyPlanRecord])
async def get_study_plan(
    request: Request,
    study_plan_id: str,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    plan = study_plan_service.get_study_plan(db, study_plan_id)
    return {"data": plan, "request_id": request.state.request_id}


@router.patch(
    "/{study_plan_id}/tasks/{task_id}",
    response_model=ApiResponse[StudyPlanRecord],
)
async def update_study_plan_task_status(
    request: Request,
    study_plan_id: str,
    task_id: str,
    payload: StudyTaskStatusUpdateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    plan = study_plan_service.update_task_status(db, study_plan_id, task_id, payload)
    return {"data": plan, "request_id": request.state.request_id}
