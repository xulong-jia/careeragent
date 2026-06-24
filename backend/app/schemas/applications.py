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
    status: str = "saved"
    apply_date: date | None = None
    next_step_date: date | None = None
    interview_notes: str | None = None
    reflection: str | None = None
    tags: list[str] = Field(default_factory=list)


class ApplicationUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str | None = Field(default=None, max_length=160)
    role_title: str | None = Field(default=None, max_length=200)
    role_category: str | None = Field(default=None, max_length=160)
    jd_id: str | None = Field(default=None, max_length=64)
    resume_version_id: str | None = Field(default=None, max_length=64)
    match_report_id: str | None = Field(default=None, max_length=64)
    status: str | None = None
    apply_date: date | None = None
    next_step_date: date | None = None
    interview_notes: str | None = None
    reflection: str | None = None
    tags: list[str] | None = None


class ApplicationRecord(BaseModel):
    application_id: str
    user_id: str
    company: str
    role_title: str
    role_category: str | None = None
    jd_id: str | None = None
    resume_version_id: str | None = None
    match_report_id: str | None = None
    status: str
    apply_date: date | None = None
    next_step_date: date | None = None
    interview_notes: str | None = None
    reflection: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ApplicationStats(BaseModel):
    total_applications: int
    by_status: dict[str, int] = Field(default_factory=dict)
    interview_count: int
    offer_count: int
    rejected_count: int
    active_count: int
