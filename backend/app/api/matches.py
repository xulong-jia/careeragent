from fastapi import APIRouter, Request, status

from app.schemas.common import ApiResponse, ListResponse
from app.schemas.matches import MatchReport, MatchRunRequest
from app.services.match_service import (
    build_mock_report,
    get_mock_match,
    list_mock_matches,
)


router = APIRouter(prefix="/api/matches", tags=["matches"])


@router.post(
    "/run",
    response_model=ApiResponse[MatchReport],
    status_code=status.HTTP_201_CREATED,
)
async def run_match(
    request: Request, payload: MatchRunRequest
) -> dict[str, object]:
    report = build_mock_report(payload)
    return {"data": report, "request_id": request.state.request_id}


@router.get("", response_model=ApiResponse[ListResponse[MatchReport]])
async def list_matches(request: Request) -> dict[str, object]:
    items = list_mock_matches()
    return {
        "data": ListResponse(items=items, total=len(items)),
        "request_id": request.state.request_id,
    }


@router.get("/{match_report_id}", response_model=ApiResponse[MatchReport])
async def get_match(
    request: Request, match_report_id: str
) -> dict[str, object]:
    report = get_mock_match(match_report_id)
    return {"data": report, "request_id": request.state.request_id}
