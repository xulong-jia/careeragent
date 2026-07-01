from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MatchRunRequest(BaseModel):
    resume_id: str | None = Field(default=None, min_length=1)
    resume_version_id: str | None = Field(default=None, min_length=1)
    jd_id: str = Field(min_length=1)


class MatchCompareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jd_id: str | None = Field(default=None, min_length=1)
    resume_version_ids: list[str] = Field(default_factory=list)
    resume_version_id: str | None = Field(default=None, min_length=1)
    jd_ids: list[str] = Field(default_factory=list)


class MatchEvidence(BaseModel):
    dimension: str
    jd_requirement: str
    resume_signal: str | None = None
    score_impact: str
    source: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class MatchReport(BaseModel):
    match_report_id: str
    resume_id: str
    resume_version_id: str | None = None
    jd_id: str
    job_profile_id: str | None = None
    total_score: int
    dimension_scores: dict[str, int]
    evidence: list[MatchEvidence] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    rewrite_priorities: list[str] = Field(default_factory=list)
    risk_flags: list[dict[str, object]] = Field(default_factory=list)
    recommended_projects: list[dict[str, object]] = Field(default_factory=list)
    score_breakdown: dict[str, object] = Field(default_factory=dict)
    scoring_method: str = "deterministic_trustworthy_match_v1"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime | None = None


class MatchCompareItem(BaseModel):
    rank: int
    match_report_id: str
    resume_id: str
    resume_version_id: str | None = None
    jd_id: str
    total_score: int
    score_delta_from_top: int
    main_strengths: list[str] = Field(default_factory=list)
    main_gaps: list[str] = Field(default_factory=list)
    risk_flags: list[dict[str, object]] = Field(default_factory=list)
    dimension_scores: dict[str, int] = Field(default_factory=dict)


class MatchCompareResponse(BaseModel):
    compare_mode: str
    sort_key: str = "total_score_desc"
    items: list[MatchCompareItem]
