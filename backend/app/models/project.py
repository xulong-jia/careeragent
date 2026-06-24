from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_projects_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), default="default", nullable=False, index=True
    )
    profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("profiles.id", ondelete="SET NULL"),
        index=True,
    )
    resume_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="SET NULL"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str | None] = mapped_column(String(160))
    period: Mapped[str | None] = mapped_column(String(160))
    background: Mapped[str | None] = mapped_column(Text)
    tech_stack: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    responsibilities: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    results: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidence: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
