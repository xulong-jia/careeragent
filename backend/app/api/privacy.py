from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse, ListResponse
from app.services import privacy_service


router = APIRouter(prefix="/api/privacy", tags=["privacy"])


@router.get("/export", response_model=ApiResponse[dict[str, object]])
async def export_privacy_data(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    data = privacy_service.export_current_user_data(db)
    return {"data": data, "request_id": request.state.request_id}


@router.delete("/delete-all", response_model=ApiResponse[dict[str, object]])
async def delete_all_privacy_data(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    data = privacy_service.delete_current_user_data(db)
    return {"data": data, "request_id": request.state.request_id}


@router.get("/audit-log", response_model=ApiResponse[ListResponse[dict[str, object]]])
async def list_privacy_audit_log(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    items = privacy_service.list_audit_logs(db)
    return {
        "data": ListResponse(items=items, total=len(items)),
        "request_id": request.state.request_id,
    }
