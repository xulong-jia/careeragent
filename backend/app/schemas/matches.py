from datetime import datetime

from pydantic import BaseModel, Field


class MatchRunRequest(BaseModel):
    resume_id: str | None = Field(default=None, min_length=1)
    resume_version_id: str | None = Field(default=None, min_length=1)
    jd_id: str = Field(min_length=1)


class MatchEvidence(BaseModel):
    dimension: str
    jd_requirement: str
    resume_signal: str | None = None
    score_impact: str


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
    created_at: datetime | None = None
