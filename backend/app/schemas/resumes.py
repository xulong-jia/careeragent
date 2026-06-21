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
