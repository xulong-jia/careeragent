from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse, ListResponse
from app.schemas.evaluations import (
    BadCaseCreateRequest,
    BadCaseRecord,
    BadCaseUpdateRequest,
)
from app.services import evaluation_service


router = APIRouter(prefix="/api/evaluations/bad-cases", tags=["evaluations"])


@router.post(
    "",
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


@router.get("", response_model=ApiResponse[ListResponse[BadCaseRecord]])
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


@router.get("/{bad_case_id}", response_model=ApiResponse[BadCaseRecord])
async def get_bad_case(
    request: Request,
    bad_case_id: str,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    bad_case = evaluation_service.get_bad_case(db, bad_case_id)
    return {"data": bad_case, "request_id": request.state.request_id}


@router.patch("/{bad_case_id}", response_model=ApiResponse[BadCaseRecord])
async def update_bad_case(
    request: Request,
    bad_case_id: str,
    payload: BadCaseUpdateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    bad_case = evaluation_service.update_bad_case(db, bad_case_id, payload)
    return {"data": bad_case, "request_id": request.state.request_id}
