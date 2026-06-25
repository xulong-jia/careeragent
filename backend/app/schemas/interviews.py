from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


InterviewQuestionType = Literal[
    "project_deep_dive",
    "technical_depth",
    "jd_skill_check",
    "risk_or_gap_explanation",
    "behavior_or_collaboration",
    "resume_challenge",
]
InterviewDifficulty = Literal["easy", "medium", "hard"]


class InterviewSourceRef(BaseModel):
    source_type: str
    source_id: str
    field: str
    label: str
    preview: str


class InterviewQuestionGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jd_id: str = Field(min_length=1, max_length=64)
    resume_version_id: str = Field(min_length=1, max_length=64)
    project_id: str | None = Field(default=None, max_length=64)
    project_rewrite_id: str | None = Field(default=None, max_length=64)
    question_types: list[InterviewQuestionType] | None = None
    max_questions: int = Field(default=6, ge=1, le=12)


class InterviewQuestionRecord(BaseModel):
    id: str
    user_id: str
    jd_id: str
    resume_version_id: str
    project_id: str | None = None
    project_rewrite_id: str | None = None
    question_type: InterviewQuestionType
    question: str
    expected_points: list[dict[str, object]] = Field(default_factory=list)
    source_refs: list[InterviewSourceRef] = Field(default_factory=list)
    difficulty: InterviewDifficulty
    created_at: datetime


class InterviewQuestionGenerateResponse(BaseModel):
    questions: list[InterviewQuestionRecord] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    need_more_info: list[str] = Field(default_factory=list)


class InterviewAnswerCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(min_length=1, max_length=64)
    answer_text: str = Field(max_length=20000)


class InterviewAnswerScoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InterviewAnswerRecord(BaseModel):
    id: str
    question_id: str
    user_id: str
    answer_text_preview: str
    scores: dict[str, float] = Field(default_factory=dict)
    feedback: str | None = None
    weakness_tags: list[str] = Field(default_factory=list)
    created_at: datetime


class InterviewAnswerScoreResponse(BaseModel):
    answer: InterviewAnswerRecord
