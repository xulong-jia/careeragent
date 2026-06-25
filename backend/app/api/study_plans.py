from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.study_plans import StudyPlanGenerateRequest, StudyPlanRecord
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
