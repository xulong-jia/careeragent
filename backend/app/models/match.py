from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MatchReport(Base):
    __tablename__ = "match_reports"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    resume_version_id: Mapped[str] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    jd_id: Mapped[str] = mapped_column(
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("job_profiles.id", ondelete="SET NULL"),
        index=True,
    )
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    dimension_scores: Mapped[dict] = mapped_column(JSON, nullable=False)
    evidence: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    strengths: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    gaps: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    rewrite_priorities: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    risk_flags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    resume_version: Mapped["ResumeVersion"] = relationship(back_populates="match_reports")
    job_description: Mapped["JobDescription"] = relationship(back_populates="match_reports")
    job_profile: Mapped["JobProfile | None"] = relationship(back_populates="match_reports")
