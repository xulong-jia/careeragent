from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StudyPlan(Base):
    __tablename__ = "study_plans"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'completed', 'archived')",
            name="ck_study_plans_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), default="default", nullable=False, index=True
    )
    match_report_id: Mapped[str | None] = mapped_column(
        ForeignKey("match_reports.id", ondelete="SET NULL"),
        index=True,
    )
    profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("profiles.id", ondelete="SET NULL"),
        index=True,
    )
    project_rewrite_id: Mapped[str | None] = mapped_column(
        ForeignKey("project_rewrites.id", ondelete="SET NULL"),
        index=True,
    )
    target_role: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    source_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    phases: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
