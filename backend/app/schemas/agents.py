from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AgentRunRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    workflow_name: str
    status: str
    input_refs: dict[str, object] = Field(default_factory=dict)
    output_refs: dict[str, object] = Field(default_factory=dict)
    missing_slots: list[dict[str, object]] | None = None
    questions: list[dict[str, object]] | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None


class AgentStepRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    step_name: str
    step_order: int
    status: str
    input_refs: dict[str, object] = Field(default_factory=dict)
    output_refs: dict[str, object] = Field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
