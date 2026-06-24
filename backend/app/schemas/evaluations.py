from datetime import datetime
from typing import Any

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


class EvaluationRunCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    module: str | None = Field(default=None, max_length=40)
    dataset_name: str = Field(default="synthetic_smoke_v1", min_length=1, max_length=120)
    name: str | None = Field(default=None, max_length=200)


class EvaluationCaseCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    module: str = Field(min_length=1, max_length=40)
    dataset_name: str = Field(default="synthetic_smoke_v1", min_length=1, max_length=120)
    case_name: str = Field(min_length=1, max_length=200)
    input_payload: dict[str, Any] = Field(default_factory=dict)
    expected_output: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    source_type: str = Field(default="manual", min_length=1, max_length=40)
    bad_case_id: str | None = Field(default=None, max_length=64)


class EvaluationRunRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    module: str
    dataset_name: str
    status: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    run_config: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime


class EvaluationCaseRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    module: str
    dataset_name: str
    case_name: str
    input_payload: dict[str, Any] = Field(default_factory=dict)
    expected_output: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    source_type: str
    bad_case_id: str | None = None
    created_at: datetime
    updated_at: datetime


class EvaluationResultRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    case_id: str
    module: str
    status: str
    actual_output: dict[str, Any] = Field(default_factory=dict)
    expected_output: dict[str, Any] = Field(default_factory=dict)
    passed: bool
    score: float
    error: str | None = None
    created_at: datetime


class EvaluationRunSummary(BaseModel):
    run: EvaluationRunRecord
    results_count: int


class EvaluationStats(BaseModel):
    total_runs: int
    latest_run_status: str | None = None
    latest_pass_rate: float | None = None
    total_cases: int
    failed_results: int
    by_module: dict[str, int] = Field(default_factory=dict)
