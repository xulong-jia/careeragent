from fastapi import APIRouter, Body, Depends, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse, ListResponse
from app.schemas.interviews import (
    InterviewAnswerCreateRequest,
    InterviewAnswerRecord,
    InterviewAnswerScoreRequest,
    InterviewDifficulty,
    InterviewQuestionGenerateRequest,
    InterviewQuestionGenerateResponse,
    InterviewQuestionRecord,
    InterviewQuestionType,
    InterviewStatsResponse,
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


@router.post(
    "/answers",
    response_model=ApiResponse[InterviewAnswerRecord],
    status_code=status.HTTP_201_CREATED,
)
async def submit_interview_answer(
    request: Request,
    payload: InterviewAnswerCreateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    answer = interview_service.submit_answer(db, payload)
    return {"data": answer, "request_id": request.state.request_id}


@router.get(
    "/answers",
    response_model=ApiResponse[ListResponse[InterviewAnswerRecord]],
)
async def list_interview_answers(
    request: Request,
    question_id: str | None = None,
    jd_id: str | None = None,
    resume_version_id: str | None = None,
    project_id: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    answers = interview_service.list_answers(
        db,
        question_id=question_id,
        jd_id=jd_id,
        resume_version_id=resume_version_id,
        project_id=project_id,
    )
    return {
        "data": ListResponse(items=answers, total=len(answers)),
        "request_id": request.state.request_id,
    }


@router.get("/stats", response_model=ApiResponse[InterviewStatsResponse])
async def get_interview_stats(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    stats = interview_service.get_stats(db)
    return {"data": stats, "request_id": request.state.request_id}


@router.post(
    "/answers/{answer_id}/score",
    response_model=ApiResponse[InterviewAnswerRecord],
)
async def score_interview_answer(
    request: Request,
    answer_id: str,
    payload: InterviewAnswerScoreRequest | None = Body(default=None),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    answer = interview_service.score_answer(db, answer_id, payload)
    return {"data": answer, "request_id": request.state.request_id}
