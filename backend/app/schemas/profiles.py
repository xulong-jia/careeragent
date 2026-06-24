from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProfileCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_roles: list[str] = Field(default_factory=list)
    target_industries: list[str] = Field(default_factory=list)
    target_locations: list[str] = Field(default_factory=list)
    skill_map: dict[str, object] = Field(default_factory=dict)
    preferences: dict[str, object] = Field(default_factory=dict)
    source_resume_version_id: str | None = Field(default=None, max_length=64)


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_roles: list[str] | None = None
    target_industries: list[str] | None = None
    target_locations: list[str] | None = None
    skill_map: dict[str, object] | None = None
    preferences: dict[str, object] | None = None
    source_resume_version_id: str | None = Field(default=None, max_length=64)


class ProfileRecord(BaseModel):
    id: str
    user_id: str
    target_roles: list[str] = Field(default_factory=list)
    target_industries: list[str] = Field(default_factory=list)
    target_locations: list[str] = Field(default_factory=list)
    skill_map: dict[str, object] = Field(default_factory=dict)
    preferences: dict[str, object] = Field(default_factory=dict)
    source_resume_version_id: str | None = None
    created_at: datetime
    updated_at: datetime


class ProfileSummary(BaseModel):
    profile_id: str
    completeness_score: int
    missing_fields: list[str] = Field(default_factory=list)
    target_roles_count: int
    target_locations_count: int
    skill_categories_count: int
    source_resume_version_id: str | None = None
    readiness_level: Literal["incomplete", "basic", "ready"]
