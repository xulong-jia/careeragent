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


class ProjectRewriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jd_id: str = Field(min_length=1, max_length=64)
    resume_version_id: str | None = Field(default=None, max_length=64)
    match_report_id: str | None = Field(default=None, max_length=64)
    profile_id: str | None = Field(default=None, max_length=64)


class ProjectMatchedPoint(BaseModel):
    skill: str
    source_field: str
    project_text: str
    jd_requirement: str
    match_type: Literal[
        "required_skill",
        "preferred_skill",
        "responsibility",
        "business_scenario",
    ]


class ProjectMissingPoint(BaseModel):
    requirement: str
    requirement_type: Literal["required_skill", "preferred_skill"]
    reason: str
    priority: Literal["high", "medium"]


class ProjectEvidenceRequired(BaseModel):
    type: Literal[
        "unsupported_metric",
        "missing_evidence",
        "timeline_or_scope_evidence",
    ]
    source_field: str
    project_text: str
    reason: str


class ProjectRewrittenBullet(BaseModel):
    before: str
    after: str
    reason: str
    evidence_required: str = ""
    risk_level: Literal["low", "medium", "high"] = "low"


class ProjectRiskFlag(BaseModel):
    type: Literal[
        "unsupported_metric",
        "missing_evidence",
        "overclaim",
        "fabricated_skill",
        "learning_to_business_overclaim",
    ]
    severity: Literal["low", "medium", "high"]
    source_field: str
    message: str


class ProjectRewriteRecord(BaseModel):
    id: str
    project_id: str
    jd_id: str
    resume_version_id: str | None = None
    match_report_id: str | None = None
    profile_id: str | None = None
    matched_points: list[ProjectMatchedPoint] = Field(default_factory=list)
    missing_points: list[ProjectMissingPoint] = Field(default_factory=list)
    evidence_required: list[ProjectEvidenceRequired] = Field(default_factory=list)
    rewritten_bullets: list[ProjectRewrittenBullet] = Field(default_factory=list)
    forbidden_changes: list[str] = Field(default_factory=list)
    risk_flags: list[ProjectRiskFlag] = Field(default_factory=list)
    rewrite_strategy: str
    created_at: datetime
