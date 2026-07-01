from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False)
    workspace_id: Mapped[str] = mapped_column(
        String(64), default="default_workspace", nullable=False, index=True
    )
    company: Mapped[str] = mapped_column(String(160), nullable=False)
    job_title: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str | None] = mapped_column(String(160))
    source_url: Mapped[str | None] = mapped_column(String(500))
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    profiles: Mapped[list["JobProfile"]] = relationship(
        back_populates="job_description",
        cascade="all, delete-orphan",
    )
    match_reports: Mapped[list["MatchReport"]] = relationship(
        back_populates="job_description"
    )


class JobProfile(Base):
    __tablename__ = "job_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    jd_id: Mapped[str] = mapped_column(
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False)
    role_category: Mapped[str] = mapped_column(String(160), nullable=False)
    required_skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    preferred_skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    responsibilities: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    business_scenarios: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    hidden_requirements: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    interview_focus: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    risk_level: Mapped[str] = mapped_column(String(40), default="low", nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    parse_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    evidence: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    warnings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    parser_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    job_description: Mapped[JobDescription] = relationship(back_populates="profiles")
    match_reports: Mapped[list["MatchReport"]] = relationship(back_populates="job_profile")
