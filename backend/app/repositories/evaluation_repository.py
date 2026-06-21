from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.evaluation import BadCase
from app.schemas.evaluations import BadCaseRecord


def _next_bad_case_id(db: Session) -> str:
    count = db.scalar(select(func.count()).select_from(BadCase)) or 0
    return f"bad_case_{count + 1:04d}"


def _to_bad_case_record(bad_case: BadCase) -> BadCaseRecord:
    return BadCaseRecord.model_validate(bad_case)


def create_bad_case(
    db: Session,
    *,
    source_type: str,
    source_id: str,
    category: str,
    severity: str,
    title: str,
    description: str,
    expected_behavior: str | None = None,
    actual_behavior: str | None = None,
    suggested_fix: str | None = None,
) -> BadCaseRecord:
    bad_case = BadCase(
        id=_next_bad_case_id(db),
        source_type=source_type,
        source_id=source_id,
        category=category,
        severity=severity,
        title=title,
        description=description,
        expected_behavior=expected_behavior,
        actual_behavior=actual_behavior,
        suggested_fix=suggested_fix,
    )
    try:
        db.add(bad_case)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(bad_case)
    return _to_bad_case_record(bad_case)


def get_bad_case_model(db: Session, bad_case_id: str) -> BadCase | None:
    return db.get(BadCase, bad_case_id)


def get_bad_case(db: Session, bad_case_id: str) -> BadCaseRecord | None:
    bad_case = get_bad_case_model(db, bad_case_id)
    return _to_bad_case_record(bad_case) if bad_case else None


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
    statement = select(BadCase)
    if source_type:
        statement = statement.where(BadCase.source_type == source_type)
    if source_id:
        statement = statement.where(BadCase.source_id == source_id)
    if category:
        statement = statement.where(BadCase.category == category)
    if severity:
        statement = statement.where(BadCase.severity == severity)
    if status:
        statement = statement.where(BadCase.status == status)
    statement = statement.order_by(desc(BadCase.created_at), desc(BadCase.id)).limit(
        limit
    )
    bad_cases = db.scalars(statement).all()
    return [_to_bad_case_record(bad_case) for bad_case in bad_cases]


def update_bad_case(
    db: Session,
    bad_case: BadCase,
    *,
    status: str | None = None,
    severity: str | None = None,
    title: str | None = None,
    description: str | None = None,
    expected_behavior: str | None = None,
    actual_behavior: str | None = None,
    suggested_fix: str | None = None,
    category: str | None = None,
    resolved_at: datetime | None = None,
    clear_resolved_at: bool = False,
) -> BadCaseRecord:
    if status is not None:
        bad_case.status = status
    if severity is not None:
        bad_case.severity = severity
    if title is not None:
        bad_case.title = title
    if description is not None:
        bad_case.description = description
    if expected_behavior is not None:
        bad_case.expected_behavior = expected_behavior
    if actual_behavior is not None:
        bad_case.actual_behavior = actual_behavior
    if suggested_fix is not None:
        bad_case.suggested_fix = suggested_fix
    if category is not None:
        bad_case.category = category
    if clear_resolved_at:
        bad_case.resolved_at = None
    elif resolved_at is not None:
        bad_case.resolved_at = resolved_at

    try:
        db.add(bad_case)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(bad_case)
    return _to_bad_case_record(bad_case)
