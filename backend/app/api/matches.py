from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse, ListResponse
from app.schemas.matches import (
    MatchCompareRequest,
    MatchCompareResponse,
    MatchReport,
    MatchRunRequest,
)
from app.services.match_service import (
    compare_matches,
    get_match_report,
    list_match_reports,
    run_match_report,
)


router = APIRouter(prefix="/api/matches", tags=["matches"])


@router.post(
    "/run",
    response_model=ApiResponse[MatchReport],
    status_code=status.HTTP_201_CREATED,
)
async def run_match(
    request: Request, payload: MatchRunRequest, db: Session = Depends(get_db)
) -> dict[str, object]:
    report = run_match_report(db, payload)
    return {"data": report, "request_id": request.state.request_id}


@router.post("/compare", response_model=ApiResponse[MatchCompareResponse])
async def compare_match_reports(
    request: Request, payload: MatchCompareRequest, db: Session = Depends(get_db)
) -> dict[str, object]:
    result = compare_matches(db, payload)
    return {"data": result, "request_id": request.state.request_id}


@router.get("", response_model=ApiResponse[ListResponse[MatchReport]])
async def list_matches(
    request: Request,
    jd_id: str | None = None,
    resume_version_id: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    items = list_match_reports(
        db,
        jd_id=jd_id,
        resume_version_id=resume_version_id,
    )
    return {
        "data": ListResponse(items=items, total=len(items)),
        "request_id": request.state.request_id,
    }


@router.get("/{match_report_id}", response_model=ApiResponse[MatchReport])
async def get_match(
    request: Request, match_report_id: str, db: Session = Depends(get_db)
) -> dict[str, object]:
    report = get_match_report(db, match_report_id)
    return {"data": report, "request_id": request.state.request_id}
