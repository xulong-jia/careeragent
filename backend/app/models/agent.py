from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False)
    workspace_id: Mapped[str] = mapped_column(
        String(64), default="default_workspace", nullable=False, index=True
    )
    workflow_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(40), default="pending", nullable=False, index=True
    )
    input_refs: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    output_refs: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    final_output_ref: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    run_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    missing_slots: Mapped[list | None] = mapped_column(JSON)
    questions: Mapped[list | None] = mapped_column(JSON)
    error_code: Mapped[str | None] = mapped_column(String(120))
    error_message: Mapped[str | None] = mapped_column(Text)
    bad_case_id: Mapped[str | None] = mapped_column(String(64), index=True)
    bad_case_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    retry_attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    steps: Mapped[list["AgentStep"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="AgentStep.attempt, AgentStep.step_order",
    )

    @property
    def final_summary(self) -> dict | None:
        if not isinstance(self.output_refs, dict):
            return None
        summary = self.output_refs.get("final_summary")
        return summary if isinstance(summary, dict) else None


class AgentStep(Base):
    __tablename__ = "agent_steps"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "step_order",
            "attempt",
            name="uq_agent_steps_run_id_step_order_attempt",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_name: Mapped[str] = mapped_column(String(120), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(
        String(40), default="pending", nullable=False, index=True
    )
    input_refs: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    output_refs: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    run_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    privacy_safe_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(120))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    run: Mapped[AgentRun] = relationship(back_populates="steps")
