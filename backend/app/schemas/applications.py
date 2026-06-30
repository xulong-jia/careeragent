from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ApplicationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str = Field(min_length=1, max_length=160)
    role_title: str = Field(min_length=1, max_length=200)
    role_category: str | None = Field(default=None, max_length=160)
    jd_id: str | None = Field(default=None, max_length=64)
    resume_version_id: str | None = Field(default=None, max_length=64)
    match_report_id: str | None = Field(default=None, max_length=64)
    agent_run_id: str | None = Field(default=None, max_length=64)
    status: str = "saved"
    apply_date: date | None = None
    next_step_date: date | None = None
    source_url: str | None = Field(default=None, max_length=500)
    location: str | None = Field(default=None, max_length=160)
    priority: str = "medium"
    notes: str | None = None
    interview_notes: str | None = None
    reflection: str | None = None
    interview_question_ids: list[str] = Field(default_factory=list)
    last_contact_date: date | None = None
    tags: list[str] = Field(default_factory=list)


class ApplicationUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str | None = Field(default=None, max_length=160)
    role_title: str | None = Field(default=None, max_length=200)
    role_category: str | None = Field(default=None, max_length=160)
    jd_id: str | None = Field(default=None, max_length=64)
    resume_version_id: str | None = Field(default=None, max_length=64)
    match_report_id: str | None = Field(default=None, max_length=64)
    agent_run_id: str | None = Field(default=None, max_length=64)
    status: str | None = None
    status_reason: str | None = Field(default=None, max_length=240)
    status_note: str | None = None
    apply_date: date | None = None
    next_step_date: date | None = None
    source_url: str | None = Field(default=None, max_length=500)
    location: str | None = Field(default=None, max_length=160)
    priority: str | None = None
    notes: str | None = None
    interview_notes: str | None = None
    reflection: str | None = None
    interview_question_ids: list[str] | None = None
    last_contact_date: date | None = None
    tags: list[str] | None = None


class ApplicationStatusHistoryRecord(BaseModel):
    history_id: str
    application_id: str
    from_status: str | None = None
    to_status: str
    changed_at: datetime
    reason: str | None = None
    note: str | None = None
    created_at: datetime


class ApplicationRecord(BaseModel):
    application_id: str
    user_id: str
    company: str
    role_title: str
    role_category: str | None = None
    jd_id: str | None = None
    resume_version_id: str | None = None
    match_report_id: str | None = None
    agent_run_id: str | None = None
    status: str
    apply_date: date | None = None
    next_step_date: date | None = None
    source_url: str | None = None
    location: str | None = None
    priority: str = "medium"
    notes: str | None = None
    interview_notes: str | None = None
    reflection: str | None = None
    interview_question_ids: list[str] = Field(default_factory=list)
    last_contact_date: date | None = None
    tags: list[str] = Field(default_factory=list)
    status_history: list[ApplicationStatusHistoryRecord] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ApplicationReflectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reflection: str | None = None
    interview_notes: str | None = None
    failure_reason: str | None = Field(default=None, max_length=500)
    preparation_gaps: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    weakness_tags: list[str] = Field(default_factory=list)
    note: str | None = None


class ApplicationConversionStats(BaseModel):
    applied_to_interview_rate: float = 0
    interview_to_offer_rate: float = 0
    applied_to_offer_rate: float = 0


class ApplicationStats(BaseModel):
    total: int
    total_applications: int
    by_status: dict[str, int] = Field(default_factory=dict)
    active_count: int
    interview_count: int
    offer_count: int
    rejected_count: int
    withdrawn_count: int
    conversion: ApplicationConversionStats = Field(default_factory=ApplicationConversionStats)
    upcoming_count: int
    overdue_count: int
    latest_applications: list[ApplicationRecord] = Field(default_factory=list)
