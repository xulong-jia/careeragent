from datetime import datetime

from pydantic import BaseModel, Field


class SourceFile(BaseModel):
    filename: str
    file_type: str
    text_hash: str | None = None


class StructuredResume(BaseModel):
    basic_info: dict[str, str | None] = Field(default_factory=dict)
    education: list[dict[str, object]] = Field(default_factory=list)
    projects: list[dict[str, object]] = Field(default_factory=list)
    experience: list[dict[str, object]] = Field(default_factory=list)
    skills: dict[str, list[str]] = Field(default_factory=dict)
    certificates: list[dict[str, object]] = Field(default_factory=list)


class ResumeRecord(BaseModel):
    resume_id: str
    filename: str
    file_type: str
    parse_status: str
    raw_text: str
    raw_text_preview: str
    extraction_status: str
    extraction_method: str
    extraction_warnings: list[str] = Field(default_factory=list)
    structured_resume: StructuredResume
    source_file: SourceFile
    risk_flags: list[dict[str, object]] = Field(default_factory=list)


class ResumeVersionRecord(BaseModel):
    resume_version_id: str
    resume_id: str
    version_name: str
    version_number: int
    target_role: str | None = None
    raw_text: str
    raw_text_preview: str
    structured_resume: StructuredResume
    extraction_status: str
    extraction_method: str
    extraction_warnings: list[str] = Field(default_factory=list)
    risk_flags: list[dict[str, object]] = Field(default_factory=list)
    status: str
    is_archived: bool
    created_at: datetime
    archived_at: datetime | None = None


class ResumeVersionCloneRequest(BaseModel):
    version_name: str | None = Field(default=None, max_length=200)
    target_role: str | None = Field(default=None, max_length=160)
