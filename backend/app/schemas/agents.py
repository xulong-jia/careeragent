from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AgentRunCreateRequest(BaseModel):
    workflow_name: str
    resume_id: str | None = None
    resume_version_id: str | None = None
    jd_id: str | None = None
    project_ids: list[str] = Field(default_factory=list)
    application_id: str | None = None
    create_application: bool = True
    use_rag: bool = False
    rag_query: str | None = None
    rag_answer_run_ids: list[str] = Field(default_factory=list)


class AgentRunRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    workflow_name: str
    status: str
    input_refs: dict[str, object] = Field(default_factory=dict)
    output_refs: dict[str, object] = Field(default_factory=dict)
    final_summary: dict[str, object] | None = None
    missing_slots: list[dict[str, object]] | None = None
    questions: list[dict[str, object]] | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None


class AgentRunCreateResponse(BaseModel):
    run: AgentRunRecord
    steps_count: int | None = None


class AgentRunDetailResponse(BaseModel):
    run: AgentRunRecord
    steps_count: int | None = None


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


class AgentStepListResponse(BaseModel):
    steps: list[AgentStepRecord] = Field(default_factory=list)
    total: int
