from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), default="default", nullable=False, index=True
    )
    target_roles: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    target_industries: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    target_locations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    skill_map: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    preferences: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    source_resume_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="SET NULL"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
