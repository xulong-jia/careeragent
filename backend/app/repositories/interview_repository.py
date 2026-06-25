from uuid import uuid4
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.interview import InterviewAnswer, InterviewQuestion
from app.schemas.interviews import (
    InterviewAnswerRecord,
    InterviewQuestionRecord,
    InterviewStatsResponse,
)


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


def _next_interview_answer_id(db: Session) -> str:
    for _ in range(10):
        answer_id = f"interview_answer_{uuid4().hex[:12]}"
        if db.get(InterviewAnswer, answer_id) is None:
            return answer_id
    raise AppError(
        code="interview_answer_id_generation_failed",
        message="Unable to generate a unique interview answer id.",
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


def _to_answer_record(answer: InterviewAnswer) -> InterviewAnswerRecord:
    return InterviewAnswerRecord(
        id=answer.id,
        question_id=answer.question_id,
        user_id=answer.user_id,
        answer_text_preview=answer.answer_text_preview,
        scores=dict(answer.scores or {}),
        feedback=answer.feedback,
        weakness_tags=list(answer.weakness_tags or []),
        created_at=answer.created_at,
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


def create_answer(
    db: Session,
    *,
    question_id: str,
    answer_text: str,
    answer_text_preview: str,
) -> InterviewAnswerRecord:
    answer = InterviewAnswer(
        id=_next_interview_answer_id(db),
        question_id=question_id,
        user_id="default",
        answer_text=answer_text,
        answer_text_preview=answer_text_preview,
        scores={},
        feedback=None,
        weakness_tags=[],
    )
    try:
        db.add(answer)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(answer)
    return _to_answer_record(answer)


def list_answers(
    db: Session,
    *,
    question_id: str | None = None,
    jd_id: str | None = None,
    resume_version_id: str | None = None,
    project_id: str | None = None,
) -> list[InterviewAnswerRecord]:
    statement = select(InterviewAnswer).join(InterviewQuestion)
    if question_id is not None:
        statement = statement.where(InterviewAnswer.question_id == question_id)
    if jd_id is not None:
        statement = statement.where(InterviewQuestion.jd_id == jd_id)
    if resume_version_id is not None:
        statement = statement.where(
            InterviewQuestion.resume_version_id == resume_version_id
        )
    if project_id is not None:
        statement = statement.where(InterviewQuestion.project_id == project_id)
    answers = db.scalars(
        statement.order_by(InterviewAnswer.created_at, InterviewAnswer.id)
    ).all()
    return [_to_answer_record(answer) for answer in answers]


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


def get_question_model(db: Session, question_id: str) -> InterviewQuestion | None:
    return db.get(InterviewQuestion, question_id)


def get_question(db: Session, question_id: str) -> InterviewQuestionRecord:
    question = get_question_model(db, question_id)
    if not question:
        raise AppError(
            code="interview_question_not_found",
            message="Interview question was not found.",
            status_code=404,
            details={"question_id": question_id},
        )
    return _to_question_record(question)


def get_answer_model(db: Session, answer_id: str) -> InterviewAnswer | None:
    return db.get(InterviewAnswer, answer_id)


def get_answer(db: Session, answer_id: str) -> InterviewAnswerRecord:
    answer = get_answer_model(db, answer_id)
    if not answer:
        raise AppError(
            code="interview_answer_not_found",
            message="Interview answer was not found.",
            status_code=404,
            details={"answer_id": answer_id},
        )
    return _to_answer_record(answer)


def update_answer_score(
    db: Session,
    answer: InterviewAnswer,
    *,
    scores: dict[str, float],
    feedback: str,
    weakness_tags: list[str],
) -> InterviewAnswerRecord:
    answer.scores = scores
    answer.feedback = feedback
    answer.weakness_tags = weakness_tags
    try:
        db.add(answer)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(answer)
    return _to_answer_record(answer)


def get_stats(db: Session) -> InterviewStatsResponse:
    questions = db.scalars(select(InterviewQuestion)).all()
    answers = db.scalars(select(InterviewAnswer)).all()
    scored_answers = [
        answer
        for answer in answers
        if isinstance(answer.scores, dict)
        and isinstance(answer.scores.get("overall_average"), int | float)
    ]
    latest_scored_answer = max(
        scored_answers,
        key=lambda answer: (answer.created_at, answer.id),
        default=None,
    )
    latest_average_score = (
        float(latest_scored_answer.scores["overall_average"])
        if latest_scored_answer
        else None
    )
    latest_weakness_tags = (
        list(latest_scored_answer.weakness_tags or [])
        if latest_scored_answer
        else []
    )

    return InterviewStatsResponse(
        total_questions=len(questions),
        total_answers=len(answers),
        scored_answers=len(scored_answers),
        latest_average_score=latest_average_score,
        latest_weakness_tags=latest_weakness_tags,
        by_question_type=dict(
            Counter(question.question_type for question in questions)
        ),
        by_difficulty=dict(Counter(question.difficulty for question in questions)),
    )
