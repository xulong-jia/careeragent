from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
