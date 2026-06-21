from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.repositories import evaluation_repository
from app.schemas.evaluations import (
    BadCaseCreateRequest,
    BadCaseRecord,
    BadCaseUpdateRequest,
)


ALLOWED_SOURCE_TYPES = {
    "match_report",
    "rag_answer",
    "rag_document",
    "agent_run",
    "agent_step",
    "resume_version",
    "job_description",
    "ui_flow",
    "data_persistence",
    "other",
}
ALLOWED_CATEGORIES = {
    "match_score_inaccurate",
    "missing_skill_extraction",
    "irrelevant_rag_source",
    "unsupported_answer",
    "hallucination_risk",
    "agent_step_failed",
    "need_more_info_wrong",
    "privacy_risk",
    "ui_confusing",
    "data_persistence_issue",
    "other",
}
ALLOWED_SEVERITIES = {"low", "medium", "high", "critical"}
ALLOWED_STATUSES = {"open", "reviewing", "fixed", "wont_fix"}
RESOLVED_STATUSES = {"fixed", "wont_fix"}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _invalid_field(field: str, message: str) -> AppError:
    return AppError(
        code="bad_case_invalid_field",
        message=message,
        status_code=400,
        details={"field": field},
    )


def _normalize_required(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise _invalid_field(field, f"{field} is required.")
    return normalized


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_allowed(value: str, *, field: str, allowed_values: set[str]) -> str:
    normalized = _normalize_required(value, field).lower()
    if normalized not in allowed_values:
        raise _invalid_field(field, f"Unsupported bad case {field}.")
    return normalized


def _normalize_limit(limit: int) -> int:
    return min(max(limit, 1), 100)


def create_bad_case(db: Session, payload: BadCaseCreateRequest) -> BadCaseRecord:
    source_type = _normalize_allowed(
        payload.source_type,
        field="source_type",
        allowed_values=ALLOWED_SOURCE_TYPES,
    )
    source_id = _normalize_required(payload.source_id, "source_id")
    category = _normalize_allowed(
        payload.category,
        field="category",
        allowed_values=ALLOWED_CATEGORIES,
    )
    severity = _normalize_allowed(
        payload.severity,
        field="severity",
        allowed_values=ALLOWED_SEVERITIES,
    )
    title = _normalize_required(payload.title, "title")
    description = _normalize_required(payload.description, "description")

    return evaluation_repository.create_bad_case(
        db,
        source_type=source_type,
        source_id=source_id,
        category=category,
        severity=severity,
        title=title,
        description=description,
        expected_behavior=_normalize_optional(payload.expected_behavior),
        actual_behavior=_normalize_optional(payload.actual_behavior),
        suggested_fix=_normalize_optional(payload.suggested_fix),
    )


def list_bad_cases(
    db: Session,
    *,
    source_type: str | None = None,
    source_id: str | None = None,
    category: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[BadCaseRecord]:
    normalized_source_type = (
        _normalize_allowed(
            source_type,
            field="source_type",
            allowed_values=ALLOWED_SOURCE_TYPES,
        )
        if source_type
        else None
    )
    normalized_category = (
        _normalize_allowed(
            category,
            field="category",
            allowed_values=ALLOWED_CATEGORIES,
        )
        if category
        else None
    )
    normalized_severity = (
        _normalize_allowed(
            severity,
            field="severity",
            allowed_values=ALLOWED_SEVERITIES,
        )
        if severity
        else None
    )
    normalized_status = (
        _normalize_allowed(status, field="status", allowed_values=ALLOWED_STATUSES)
        if status
        else None
    )
    return evaluation_repository.list_bad_cases(
        db,
        source_type=normalized_source_type,
        source_id=_normalize_optional(source_id),
        category=normalized_category,
        severity=normalized_severity,
        status=normalized_status,
        limit=_normalize_limit(limit),
    )


def get_bad_case(db: Session, bad_case_id: str) -> BadCaseRecord:
    bad_case = evaluation_repository.get_bad_case(db, bad_case_id)
    if not bad_case:
        raise AppError(
            code="bad_case_not_found",
            message="Bad case was not found.",
            status_code=404,
            details={"bad_case_id": bad_case_id},
        )
    return bad_case


def update_bad_case(
    db: Session,
    bad_case_id: str,
    payload: BadCaseUpdateRequest,
) -> BadCaseRecord:
    bad_case = evaluation_repository.get_bad_case_model(db, bad_case_id)
    if not bad_case:
        raise AppError(
            code="bad_case_not_found",
            message="Bad case was not found.",
            status_code=404,
            details={"bad_case_id": bad_case_id},
        )

    update_data: dict[str, Any] = payload.model_dump(exclude_unset=True)
    status = (
        _normalize_allowed(
            update_data["status"],
            field="status",
            allowed_values=ALLOWED_STATUSES,
        )
        if "status" in update_data and update_data["status"] is not None
        else None
    )
    severity = (
        _normalize_allowed(
            update_data["severity"],
            field="severity",
            allowed_values=ALLOWED_SEVERITIES,
        )
        if "severity" in update_data and update_data["severity"] is not None
        else None
    )
    category = (
        _normalize_allowed(
            update_data["category"],
            field="category",
            allowed_values=ALLOWED_CATEGORIES,
        )
        if "category" in update_data and update_data["category"] is not None
        else None
    )
    title = (
        _normalize_required(update_data["title"], "title")
        if "title" in update_data and update_data["title"] is not None
        else None
    )
    description = (
        _normalize_required(update_data["description"], "description")
        if "description" in update_data and update_data["description"] is not None
        else None
    )

    resolved_at = None
    clear_resolved_at = False
    if status in RESOLVED_STATUSES and bad_case.resolved_at is None:
        resolved_at = _now()
    elif status in {"open", "reviewing"}:
        clear_resolved_at = True

    return evaluation_repository.update_bad_case(
        db,
        bad_case,
        status=status,
        severity=severity,
        title=title,
        description=description,
        expected_behavior=_normalize_optional(update_data.get("expected_behavior"))
        if "expected_behavior" in update_data
        else None,
        actual_behavior=_normalize_optional(update_data.get("actual_behavior"))
        if "actual_behavior" in update_data
        else None,
        suggested_fix=_normalize_optional(update_data.get("suggested_fix"))
        if "suggested_fix" in update_data
        else None,
        category=category,
        resolved_at=resolved_at,
        clear_resolved_at=clear_resolved_at,
    )
