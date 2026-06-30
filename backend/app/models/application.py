from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False)
    company: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    role_title: Mapped[str] = mapped_column(String(200), nullable=False)
    role_category: Mapped[str | None] = mapped_column(String(160), index=True)
    jd_id: Mapped[str | None] = mapped_column(
        ForeignKey("job_descriptions.id", ondelete="SET NULL"),
        index=True,
    )
    resume_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="SET NULL"),
        index=True,
    )
    match_report_id: Mapped[str | None] = mapped_column(
        ForeignKey("match_reports.id", ondelete="SET NULL"),
        index=True,
    )
    agent_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        index=True,
    )
    status: Mapped[str] = mapped_column(String(40), default="saved", nullable=False, index=True)
    apply_date: Mapped[date | None] = mapped_column(Date)
    next_step_date: Mapped[date | None] = mapped_column(Date)
    source_url: Mapped[str | None] = mapped_column(String(500))
    location: Mapped[str | None] = mapped_column(String(160), index=True)
    priority: Mapped[str] = mapped_column(String(40), default="medium", nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    interview_notes: Mapped[str | None] = mapped_column(Text)
    reflection: Mapped[str | None] = mapped_column(Text)
    interview_question_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    last_contact_date: Mapped[date | None] = mapped_column(Date)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ApplicationStatusHistory(Base):
    __tablename__ = "application_status_history"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[str | None] = mapped_column(String(40))
    to_status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(240))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
