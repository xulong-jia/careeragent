from pydantic import BaseModel, Field, HttpUrl


class JobCreateRequest(BaseModel):
    company: str = Field(min_length=1, max_length=120)
    job_title: str = Field(min_length=1, max_length=160)
    location: str | None = Field(default=None, max_length=120)
    raw_text: str = Field(min_length=1, max_length=20000)
    source_url: HttpUrl | None = None


class JobProfile(BaseModel):
    job_profile_id: str
    role_category: str
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    business_scenarios: list[str] = Field(default_factory=list)
    hidden_requirements: list[dict[str, object]] = Field(default_factory=list)
    interview_focus: list[str] = Field(default_factory=list)
    risk_level: str = "low"
    summary: str | None = None


class JobRecord(BaseModel):
    jd_id: str
    company: str
    job_title: str
    location: str | None = None
    raw_text: str
    source_url: str | None = None
    job_profile: JobProfile
