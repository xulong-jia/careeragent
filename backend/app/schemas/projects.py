from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ProjectStatus = Literal["active", "archived"]


class ProjectCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str | None = Field(default=None, max_length=64)
    resume_version_id: str | None = Field(default=None, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    role: str | None = Field(default=None, max_length=160)
    period: str | None = Field(default=None, max_length=160)
    background: str | None = Field(default=None, max_length=8000)
    tech_stack: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    results: list[str] = Field(default_factory=list)
    evidence: list[dict[str, object]] = Field(default_factory=list)
    status: ProjectStatus = "active"


class ProjectUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str | None = Field(default=None, max_length=64)
    resume_version_id: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, max_length=160)
    period: str | None = Field(default=None, max_length=160)
    background: str | None = Field(default=None, max_length=8000)
    tech_stack: list[str] | None = None
    responsibilities: list[str] | None = None
    results: list[str] | None = None
    evidence: list[dict[str, object]] | None = None
    status: ProjectStatus | None = None


class ProjectRecord(BaseModel):
    id: str
    user_id: str
    profile_id: str | None = None
    resume_version_id: str | None = None
    name: str
    role: str | None = None
    period: str | None = None
    background: str | None = None
    tech_stack: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    results: list[str] = Field(default_factory=list)
    evidence: list[dict[str, object]] = Field(default_factory=list)
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
