from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


StudyPlanStatus = Literal["active", "completed", "archived"]
StudyTaskStatus = Literal["todo", "in_progress", "done", "blocked", "skipped"]
StudyTaskPriority = Literal["high", "medium", "low"]


class StudySourceRef(BaseModel):
    source_type: str
    source_id: str
    field: str
    label: str
    preview: str


class StudyPlanGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_role: str | None = Field(default=None, max_length=160)
    profile_id: str | None = Field(default=None, max_length=64)
    match_report_id: str | None = Field(default=None, max_length=64)
    project_rewrite_id: str | None = Field(default=None, max_length=64)
    interview_answer_ids: list[str] = Field(default_factory=list)
    rag_answer_run_ids: list[str] = Field(default_factory=list)
    weakness_tags: list[str] = Field(default_factory=list)
    available_hours_per_week: int = Field(default=5, ge=1, le=80)
    horizon_weeks: int = Field(default=4, ge=1, le=52)


class StudyTask(BaseModel):
    task_id: str
    title: str
    description: str
    source_gap: str
    priority: StudyTaskPriority
    status: StudyTaskStatus = "todo"
    due_hint: str | None = None
    acceptance_criteria: list[str] = Field(default_factory=list)
    evidence_required: list[str] = Field(default_factory=list)
    source_refs: list[StudySourceRef] = Field(default_factory=list)


class StudyPhase(BaseModel):
    phase_id: str
    phase: str
    goal: str
    tasks: list[StudyTask] = Field(default_factory=list)
    resources: list[dict[str, object]] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)


class StudyPlanRecord(BaseModel):
    id: str
    user_id: str
    match_report_id: str | None = None
    profile_id: str | None = None
    project_rewrite_id: str | None = None
    target_role: str
    source_refs: list[StudySourceRef] = Field(default_factory=list)
    phases: list[StudyPhase] = Field(default_factory=list)
    status: StudyPlanStatus
    created_at: datetime
    updated_at: datetime


class StudyPlanGenerateResponse(BaseModel):
    data: StudyPlanRecord
    request_id: str


class StudyTaskStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: StudyTaskStatus


class StudyPlanStatsResponse(BaseModel):
    total_plans: int
    active_plans: int
    completed_plans: int
    archived_plans: int
    pending_tasks: int
    blocked_tasks: int
    done_tasks: int
    in_progress_tasks: int
    skipped_tasks: int
    latest_plan_id: str | None = None
    latest_target_role: str | None = None
