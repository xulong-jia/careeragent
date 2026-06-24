from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.projects import ProjectRewriteRecord
from app.services import project_rewrite_service


router = APIRouter(prefix="/api/project-rewrites", tags=["project-rewrites"])


@router.get("/{rewrite_id}", response_model=ApiResponse[ProjectRewriteRecord])
async def get_project_rewrite(
    request: Request,
    rewrite_id: str,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    rewrite = project_rewrite_service.get_project_rewrite(db, rewrite_id)
    return {"data": rewrite, "request_id": request.state.request_id}
