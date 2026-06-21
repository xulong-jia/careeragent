from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BadCaseCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    severity: str = "medium"
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    expected_behavior: str | None = None
    actual_behavior: str | None = None
    suggested_fix: str | None = None


class BadCaseUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = None
    severity: str | None = None
    title: str | None = None
    description: str | None = None
    expected_behavior: str | None = None
    actual_behavior: str | None = None
    suggested_fix: str | None = None
    category: str | None = None


class BadCaseRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    source_type: str
    source_id: str
    category: str
    severity: str
    title: str
    description: str
    expected_behavior: str | None = None
    actual_behavior: str | None = None
    suggested_fix: str | None = None
    status: str
    created_at: datetime
    resolved_at: datetime | None = None
