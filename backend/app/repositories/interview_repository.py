from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.interview import InterviewQuestion
from app.schemas.interviews import InterviewQuestionRecord


def _next_interview_question_id(db: Session) -> str:
    for _ in range(10):
        question_id = f"interview_question_{uuid4().hex[:12]}"
        if db.get(InterviewQuestion, question_id) is None:
            return question_id
    raise AppError(
        code="interview_question_id_generation_failed",
        message="Unable to generate a unique interview question id.",
        status_code=500,
        details={},
    )


def _to_question_record(question: InterviewQuestion) -> InterviewQuestionRecord:
    return InterviewQuestionRecord(
        id=question.id,
        user_id=question.user_id,
        jd_id=question.jd_id,
        resume_version_id=question.resume_version_id,
        project_id=question.project_id,
        project_rewrite_id=question.project_rewrite_id,
        question_type=question.question_type,  # type: ignore[arg-type]
        question=question.question,
        expected_points=list(question.expected_points or []),
        source_refs=list(question.source_refs or []),
        difficulty=question.difficulty,  # type: ignore[arg-type]
        created_at=question.created_at,
    )


def create_questions(
    db: Session,
    *,
    jd_id: str,
    resume_version_id: str,
    project_id: str | None,
    project_rewrite_id: str | None,
    questions: list[dict[str, object]],
) -> list[InterviewQuestionRecord]:
    records = [
        InterviewQuestion(
            id=_next_interview_question_id(db),
            user_id="default",
            jd_id=jd_id,
            resume_version_id=resume_version_id,
            project_id=project_id,
            project_rewrite_id=project_rewrite_id,
            question_type=str(question["question_type"]),
            question=str(question["question"]),
            expected_points=list(question.get("expected_points") or []),
            source_refs=list(question.get("source_refs") or []),
            difficulty=str(question["difficulty"]),
        )
        for question in questions
    ]

    try:
        db.add_all(records)
        db.commit()
    except Exception:
        db.rollback()
        raise
    for record in records:
        db.refresh(record)
    return [_to_question_record(record) for record in records]


def list_questions(
    db: Session,
    *,
    jd_id: str | None = None,
    resume_version_id: str | None = None,
    project_id: str | None = None,
    question_type: str | None = None,
    difficulty: str | None = None,
) -> list[InterviewQuestionRecord]:
    statement = select(InterviewQuestion)
    if jd_id is not None:
        statement = statement.where(InterviewQuestion.jd_id == jd_id)
    if resume_version_id is not None:
        statement = statement.where(
            InterviewQuestion.resume_version_id == resume_version_id
        )
    if project_id is not None:
        statement = statement.where(InterviewQuestion.project_id == project_id)
    if question_type is not None:
        statement = statement.where(InterviewQuestion.question_type == question_type)
    if difficulty is not None:
        statement = statement.where(InterviewQuestion.difficulty == difficulty)
    records = db.scalars(
        statement.order_by(InterviewQuestion.created_at, InterviewQuestion.id)
    ).all()
    return [_to_question_record(record) for record in records]


def get_question(db: Session, question_id: str) -> InterviewQuestionRecord:
    question = db.get(InterviewQuestion, question_id)
    if not question:
        raise AppError(
            code="interview_question_not_found",
            message="Interview question was not found.",
            status_code=404,
            details={"question_id": question_id},
        )
    return _to_question_record(question)
