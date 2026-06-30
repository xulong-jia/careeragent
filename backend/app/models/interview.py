from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"
    __table_args__ = (
        CheckConstraint(
            "question_type IN ("
            "'project_deep_dive', "
            "'technical_depth', "
            "'jd_skill_check', "
            "'risk_or_gap_explanation', "
            "'behavior_or_collaboration', "
            "'resume_challenge'"
            ")",
            name="ck_interview_questions_question_type",
        ),
        CheckConstraint(
            "difficulty IN ('easy', 'medium', 'hard')",
            name="ck_interview_questions_difficulty",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), default="default", nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(64), default="default_workspace", nullable=False, index=True
    )
    jd_id: Mapped[str] = mapped_column(
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resume_version_id: Mapped[str] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        index=True,
    )
    project_rewrite_id: Mapped[str | None] = mapped_column(
        ForeignKey("project_rewrites.id", ondelete="SET NULL"),
        index=True,
    )
    question_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_points: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    answers: Mapped[list["InterviewAnswer"]] = relationship(
        back_populates="question_record",
        cascade="all, delete-orphan",
    )


class InterviewAnswer(Base):
    __tablename__ = "interview_answers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    question_id: Mapped[str] = mapped_column(
        ForeignKey("interview_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(64), default="default", nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(64), default="default_workspace", nullable=False, index=True
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text_preview: Mapped[str] = mapped_column(Text, nullable=False)
    scores: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    feedback: Mapped[str | None] = mapped_column(Text)
    weakness_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    question_record: Mapped[InterviewQuestion] = relationship(back_populates="answers")
