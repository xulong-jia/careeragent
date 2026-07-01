from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.logging import log_event
from app.core.metrics import record_domain_event
from app.db.session import get_db
from app.schemas.common import ApiResponse, ListResponse
from app.schemas.evaluations import (
    BadCaseAddToEvalRequest,
    BadCaseCreateRequest,
    BadCaseEvaluationLinkResponse,
    BadCaseRecord,
    BadCaseStats,
    BadCaseUpdateRequest,
    EvaluationCaseCreateRequest,
    EvaluationCaseRecord,
    EvaluationDatasetRecord,
    EvaluationResultRecord,
    EvaluationRunCreateRequest,
    EvaluationRunRecord,
    EvaluationRunSummary,
    EvaluationStats,
)
from app.services import evaluation_service


router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])
bad_cases_router = APIRouter(prefix="/api/bad-cases", tags=["bad-cases"])


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
    record_domain_event("evaluation.run.created")
    log_event(
        "evaluation_run_created",
        request_id=request.state.request_id,
        run_id=run.run.id,
        module=run.run.module,
        dataset_name=run.run.dataset_name,
        status=run.run.status,
        results_count=run.results_count,
    )
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
    record_domain_event("evaluation.case.created")
    log_event(
        "evaluation_case_created",
        request_id=request.state.request_id,
        case_id=evaluation_case.id,
        module=evaluation_case.module,
        dataset_name=evaluation_case.dataset_name,
        source_type=evaluation_case.source_type,
    )
    return {"data": evaluation_case, "request_id": request.state.request_id}


@router.get(
    "/datasets",
    response_model=ApiResponse[ListResponse[EvaluationDatasetRecord]],
)
async def list_evaluation_datasets(request: Request) -> dict[str, object]:
    items = evaluation_service.list_evaluation_datasets()
    return {
        "data": ListResponse(items=items, total=len(items)),
        "request_id": request.state.request_id,
    }


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
    record_domain_event("evaluation.case.created_from_bad_case")
    log_event(
        "evaluation_case_created_from_bad_case",
        request_id=request.state.request_id,
        bad_case_id=case_id,
        case_id=evaluation_case.id,
        module=evaluation_case.module,
        dataset_name=evaluation_case.dataset_name,
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


@bad_cases_router.get("/stats", response_model=ApiResponse[BadCaseStats])
async def get_bad_case_stats(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    stats = evaluation_service.get_bad_case_stats(db)
    return {"data": stats, "request_id": request.state.request_id}


@bad_cases_router.post(
    "/{bad_case_id}/add-to-eval",
    response_model=ApiResponse[BadCaseEvaluationLinkResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_bad_case_to_eval(
    request: Request,
    bad_case_id: str,
    payload: BadCaseAddToEvalRequest | None = None,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    link = evaluation_service.add_bad_case_to_eval(db, bad_case_id, payload)
    return {"data": link, "request_id": request.state.request_id}


@bad_cases_router.post(
    "",
    response_model=ApiResponse[BadCaseRecord],
    status_code=status.HTTP_201_CREATED,
)
async def create_bad_case_direct(
    request: Request,
    payload: BadCaseCreateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    bad_case = evaluation_service.create_bad_case(db, payload)
    return {"data": bad_case, "request_id": request.state.request_id}


@bad_cases_router.get("", response_model=ApiResponse[ListResponse[BadCaseRecord]])
async def list_bad_cases_direct(
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


@bad_cases_router.get("/{bad_case_id}", response_model=ApiResponse[BadCaseRecord])
async def get_bad_case_direct(
    request: Request,
    bad_case_id: str,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    bad_case = evaluation_service.get_bad_case(db, bad_case_id)
    return {"data": bad_case, "request_id": request.state.request_id}


@bad_cases_router.patch("/{bad_case_id}", response_model=ApiResponse[BadCaseRecord])
async def update_bad_case_direct(
    request: Request,
    bad_case_id: str,
    payload: BadCaseUpdateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    bad_case = evaluation_service.update_bad_case(db, bad_case_id, payload)
    return {"data": bad_case, "request_id": request.state.request_id}
