from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_file_hash: Mapped[str | None] = mapped_column(String(128))
    parse_status: Mapped[str] = mapped_column(String(40), default="parsed", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    versions: Mapped[list["ResumeVersion"]] = relationship(
        back_populates="resume",
        cascade="all, delete-orphan",
    )


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    resume_id: Mapped[str] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_name: Mapped[str] = mapped_column(String(200), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    target_role: Mapped[str | None] = mapped_column(String(160), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    raw_text_preview: Mapped[str] = mapped_column(Text, nullable=False)
    structured_resume: Mapped[dict] = mapped_column(JSON, nullable=False)
    extraction_status: Mapped[str] = mapped_column(String(60), nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(120), nullable=False)
    extraction_warnings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    risk_flags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    risk_report: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime)

    resume: Mapped[Resume] = relationship(back_populates="versions")
    match_reports: Mapped[list["MatchReport"]] = relationship(
        back_populates="resume_version"
    )
