from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse, ListResponse
from app.schemas.interviews import (
    InterviewDifficulty,
    InterviewQuestionGenerateRequest,
    InterviewQuestionGenerateResponse,
    InterviewQuestionRecord,
    InterviewQuestionType,
)
from app.services import interview_service


router = APIRouter(prefix="/api/interviews", tags=["interviews"])


@router.post(
    "/questions/generate",
    response_model=ApiResponse[InterviewQuestionGenerateResponse],
    status_code=status.HTTP_201_CREATED,
)
async def generate_interview_questions(
    request: Request,
    payload: InterviewQuestionGenerateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    result = interview_service.generate_questions(db, payload)
    return {"data": result, "request_id": request.state.request_id}


@router.get(
    "/questions",
    response_model=ApiResponse[ListResponse[InterviewQuestionRecord]],
)
async def list_interview_questions(
    request: Request,
    jd_id: str | None = None,
    resume_version_id: str | None = None,
    project_id: str | None = None,
    question_type: InterviewQuestionType | None = None,
    difficulty: InterviewDifficulty | None = None,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    questions = interview_service.list_questions(
        db,
        jd_id=jd_id,
        resume_version_id=resume_version_id,
        project_id=project_id,
        question_type=question_type,
        difficulty=difficulty,
    )
    return {
        "data": ListResponse(items=questions, total=len(questions)),
        "request_id": request.state.request_id,
    }
