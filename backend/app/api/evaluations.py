from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse, ListResponse
from app.schemas.evaluations import (
    BadCaseCreateRequest,
    BadCaseRecord,
    BadCaseUpdateRequest,
    EvaluationCaseCreateRequest,
    EvaluationCaseRecord,
    EvaluationResultRecord,
    EvaluationRunCreateRequest,
    EvaluationRunRecord,
    EvaluationRunSummary,
    EvaluationStats,
)
from app.services import evaluation_service


router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])


@router.post(
    "/runs",
    response_model=ApiResponse[EvaluationRunSummary],
    status_code=status.HTTP_201_CREATED,
)
async def create_evaluation_run(
    request: Request,
    payload: EvaluationRunCreateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    run = evaluation_service.run_evaluation(db, payload)
    return {"data": run, "request_id": request.state.request_id}


@router.get("/runs", response_model=ApiResponse[ListResponse[EvaluationRunRecord]])
async def list_evaluation_runs(
    request: Request,
    module: str | None = Query(default=None),
    dataset_name: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    items = evaluation_service.list_evaluation_runs(
        db,
        module=module,
        dataset_name=dataset_name,
        limit=limit,
    )
    return {
        "data": ListResponse(items=items, total=len(items)),
        "request_id": request.state.request_id,
    }


@router.get("/runs/{run_id}", response_model=ApiResponse[EvaluationRunSummary])
async def get_evaluation_run(
    request: Request,
    run_id: str,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    run = evaluation_service.get_evaluation_run(db, run_id)
    return {"data": run, "request_id": request.state.request_id}


@router.get(
    "/runs/{run_id}/results",
    response_model=ApiResponse[ListResponse[EvaluationResultRecord]],
)
async def list_evaluation_results(
    request: Request,
    run_id: str,
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    items = evaluation_service.list_evaluation_results(db, run_id=run_id, limit=limit)
    return {
        "data": ListResponse(items=items, total=len(items)),
        "request_id": request.state.request_id,
    }


@router.get("/cases", response_model=ApiResponse[ListResponse[EvaluationCaseRecord]])
async def list_evaluation_cases(
    request: Request,
    module: str | None = Query(default=None),
    dataset_name: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    items = evaluation_service.list_evaluation_cases(
        db,
        module=module,
        dataset_name=dataset_name,
        source_type=source_type,
        limit=limit,
    )
    return {
        "data": ListResponse(items=items, total=len(items)),
        "request_id": request.state.request_id,
    }


@router.post(
    "/cases",
    response_model=ApiResponse[EvaluationCaseRecord],
    status_code=status.HTTP_201_CREATED,
)
async def create_evaluation_case(
    request: Request,
    payload: EvaluationCaseCreateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    evaluation_case = evaluation_service.create_evaluation_case(db, payload)
    return {"data": evaluation_case, "request_id": request.state.request_id}


@router.post(
    "/cases/from-bad-case/{case_id}",
    response_model=ApiResponse[EvaluationCaseRecord],
    status_code=status.HTTP_201_CREATED,
)
async def create_evaluation_case_from_bad_case(
    request: Request,
    case_id: str,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    evaluation_case = evaluation_service.create_evaluation_case_from_bad_case(
        db,
        case_id,
    )
    return {"data": evaluation_case, "request_id": request.state.request_id}


@router.get("/stats", response_model=ApiResponse[EvaluationStats])
async def get_evaluation_stats(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    stats = evaluation_service.get_evaluation_stats(db)
    return {"data": stats, "request_id": request.state.request_id}


@router.post(
    "/bad-cases",
    response_model=ApiResponse[BadCaseRecord],
    status_code=status.HTTP_201_CREATED,
)
async def create_bad_case(
    request: Request,
    payload: BadCaseCreateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    bad_case = evaluation_service.create_bad_case(db, payload)
    return {"data": bad_case, "request_id": request.state.request_id}


@router.get("/bad-cases", response_model=ApiResponse[ListResponse[BadCaseRecord]])
async def list_bad_cases(
    request: Request,
    source_type: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    category: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    items = evaluation_service.list_bad_cases(
        db,
        source_type=source_type,
        source_id=source_id,
        category=category,
        severity=severity,
        status=status,
        limit=limit,
    )
    return {
        "data": ListResponse(items=items, total=len(items)),
        "request_id": request.state.request_id,
    }


@router.get("/bad-cases/{bad_case_id}", response_model=ApiResponse[BadCaseRecord])
async def get_bad_case(
    request: Request,
    bad_case_id: str,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    bad_case = evaluation_service.get_bad_case(db, bad_case_id)
    return {"data": bad_case, "request_id": request.state.request_id}


@router.patch("/bad-cases/{bad_case_id}", response_model=ApiResponse[BadCaseRecord])
async def update_bad_case(
    request: Request,
    bad_case_id: str,
    payload: BadCaseUpdateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    bad_case = evaluation_service.update_bad_case(db, bad_case_id, payload)
    return {"data": bad_case, "request_id": request.state.request_id}
