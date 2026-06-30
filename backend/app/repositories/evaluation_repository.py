from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.evaluation import BadCase, EvaluationCase, EvaluationResult, EvaluationRun
from app.schemas.evaluations import (
    BadCaseRecord,
    EvaluationCaseRecord,
    EvaluationResultRecord,
    EvaluationRunRecord,
)


def _next_bad_case_id(db: Session) -> str:
    count = db.scalar(select(func.count()).select_from(BadCase)) or 0
    return f"bad_case_{count + 1:04d}"


def _next_model_id(db: Session, model, prefix: str) -> str:
    for _ in range(10):
        candidate = f"{prefix}_{uuid4().hex[:12]}"
        if db.get(model, candidate) is None:
            return candidate
    raise AppError(
        code="evaluation_id_generation_failed",
        message="Unable to generate a unique evaluation id.",
        status_code=500,
        details={"prefix": prefix},
    )


def _to_bad_case_record(bad_case: BadCase) -> BadCaseRecord:
    return BadCaseRecord.model_validate(bad_case)


def _to_run_record(run: EvaluationRun) -> EvaluationRunRecord:
    return EvaluationRunRecord.model_validate(run)


def _to_case_record(evaluation_case: EvaluationCase) -> EvaluationCaseRecord:
    return EvaluationCaseRecord.model_validate(evaluation_case)


def _to_result_record(result: EvaluationResult) -> EvaluationResultRecord:
    return EvaluationResultRecord.model_validate(result)


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
    root_cause: str | None = None,
    fix_strategy: str | None = None,
    tags: list[str] | None = None,
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
        root_cause=root_cause,
        fix_strategy=fix_strategy,
        tags=tags or [],
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
    root_cause: str | None = None,
    fix_strategy: str | None = None,
    tags: list[str] | None = None,
    added_to_eval_set: bool | None = None,
    resolved_at: datetime | None = None,
    clear_resolved_at: bool = False,
    verified_at: datetime | None = None,
    clear_verified_at: bool = False,
    regression_evaluation_run_id: str | None = None,
    regression_evaluation_case_id: str | None = None,
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
    if root_cause is not None:
        bad_case.root_cause = root_cause
    if fix_strategy is not None:
        bad_case.fix_strategy = fix_strategy
    if tags is not None:
        bad_case.tags = tags
    if added_to_eval_set is not None:
        bad_case.added_to_eval_set = added_to_eval_set
    if clear_resolved_at:
        bad_case.resolved_at = None
    elif resolved_at is not None:
        bad_case.resolved_at = resolved_at
    if clear_verified_at:
        bad_case.verified_at = None
    elif verified_at is not None:
        bad_case.verified_at = verified_at
    if regression_evaluation_run_id is not None:
        bad_case.regression_evaluation_run_id = regression_evaluation_run_id
    if regression_evaluation_case_id is not None:
        bad_case.regression_evaluation_case_id = regression_evaluation_case_id

    try:
        db.add(bad_case)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(bad_case)
    return _to_bad_case_record(bad_case)


def create_evaluation_run(
    db: Session,
    *,
    name: str,
    module: str,
    dataset_name: str,
    status: str,
    metrics: dict[str, Any],
    run_config: dict[str, Any],
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
) -> EvaluationRunRecord:
    run = EvaluationRun(
        id=_next_model_id(db, EvaluationRun, "eval_run"),
        name=name,
        module=module,
        dataset_name=dataset_name,
        status=status,
        metrics=metrics,
        run_config=run_config,
        started_at=started_at,
        finished_at=finished_at,
    )
    try:
        db.add(run)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(run)
    return _to_run_record(run)


def get_evaluation_run_model(db: Session, run_id: str) -> EvaluationRun | None:
    return db.get(EvaluationRun, run_id)


def get_evaluation_run(db: Session, run_id: str) -> EvaluationRunRecord | None:
    run = get_evaluation_run_model(db, run_id)
    return _to_run_record(run) if run else None


def list_evaluation_runs(
    db: Session,
    *,
    module: str | None = None,
    dataset_name: str | None = None,
    limit: int = 50,
) -> list[EvaluationRunRecord]:
    statement = select(EvaluationRun)
    if module:
        statement = statement.where(EvaluationRun.module == module)
    if dataset_name:
        statement = statement.where(EvaluationRun.dataset_name == dataset_name)
    statement = statement.order_by(desc(EvaluationRun.created_at), desc(EvaluationRun.id)).limit(
        limit
    )
    return [_to_run_record(run) for run in db.scalars(statement).all()]


def update_evaluation_run(
    db: Session,
    run: EvaluationRun,
    *,
    status: str | None = None,
    metrics: dict[str, Any] | None = None,
    finished_at: datetime | None = None,
) -> EvaluationRunRecord:
    if status is not None:
        run.status = status
    if metrics is not None:
        run.metrics = metrics
    if finished_at is not None:
        run.finished_at = finished_at
    try:
        db.add(run)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(run)
    return _to_run_record(run)


def create_evaluation_case(
    db: Session,
    *,
    module: str,
    dataset_name: str,
    case_name: str,
    input_payload: dict[str, Any],
    expected_output: dict[str, Any],
    tags: list[str],
    source_type: str,
    bad_case_id: str | None = None,
) -> EvaluationCaseRecord:
    evaluation_case = EvaluationCase(
        id=_next_model_id(db, EvaluationCase, "eval_case"),
        module=module,
        dataset_name=dataset_name,
        case_name=case_name,
        input_payload=input_payload,
        expected_output=expected_output,
        tags=tags,
        source_type=source_type,
        bad_case_id=bad_case_id,
    )
    try:
        db.add(evaluation_case)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(evaluation_case)
    return _to_case_record(evaluation_case)


def get_evaluation_case_model(
    db: Session, evaluation_case_id: str
) -> EvaluationCase | None:
    return db.get(EvaluationCase, evaluation_case_id)


def get_evaluation_case(
    db: Session, evaluation_case_id: str
) -> EvaluationCaseRecord | None:
    evaluation_case = get_evaluation_case_model(db, evaluation_case_id)
    return _to_case_record(evaluation_case) if evaluation_case else None


def find_evaluation_case(
    db: Session,
    *,
    module: str,
    dataset_name: str,
    case_name: str,
    source_type: str,
) -> EvaluationCaseRecord | None:
    evaluation_case = db.scalars(
        select(EvaluationCase)
        .where(EvaluationCase.module == module)
        .where(EvaluationCase.dataset_name == dataset_name)
        .where(EvaluationCase.case_name == case_name)
        .where(EvaluationCase.source_type == source_type)
        .limit(1)
    ).first()
    return _to_case_record(evaluation_case) if evaluation_case else None


def find_evaluation_case_for_bad_case(
    db: Session,
    *,
    bad_case_id: str,
    dataset_name: str,
    source_type: str = "bad_case",
) -> EvaluationCaseRecord | None:
    evaluation_case = db.scalars(
        select(EvaluationCase)
        .where(EvaluationCase.bad_case_id == bad_case_id)
        .where(EvaluationCase.dataset_name == dataset_name)
        .where(EvaluationCase.source_type == source_type)
        .limit(1)
    ).first()
    return _to_case_record(evaluation_case) if evaluation_case else None


def list_evaluation_cases(
    db: Session,
    *,
    module: str | None = None,
    dataset_name: str | None = None,
    source_type: str | None = None,
    limit: int = 100,
) -> list[EvaluationCaseRecord]:
    statement = select(EvaluationCase)
    if module:
        statement = statement.where(EvaluationCase.module == module)
    if dataset_name:
        statement = statement.where(EvaluationCase.dataset_name == dataset_name)
    if source_type:
        statement = statement.where(EvaluationCase.source_type == source_type)
    statement = statement.order_by(
        desc(EvaluationCase.created_at),
        desc(EvaluationCase.id),
    ).limit(limit)
    return [_to_case_record(evaluation_case) for evaluation_case in db.scalars(statement).all()]


def create_evaluation_result(
    db: Session,
    *,
    run_id: str,
    case_id: str,
    module: str,
    status: str,
    actual_output: dict[str, Any],
    expected_output: dict[str, Any],
    passed: bool,
    score: float,
    error: str | None = None,
) -> EvaluationResultRecord:
    result = EvaluationResult(
        id=_next_model_id(db, EvaluationResult, "eval_result"),
        run_id=run_id,
        case_id=case_id,
        module=module,
        status=status,
        actual_output=actual_output,
        expected_output=expected_output,
        passed=passed,
        score=score,
        error=error,
    )
    try:
        db.add(result)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(result)
    return _to_result_record(result)


def list_evaluation_results(
    db: Session,
    *,
    run_id: str | None = None,
    module: str | None = None,
    limit: int = 200,
) -> list[EvaluationResultRecord]:
    statement = select(EvaluationResult)
    if run_id:
        statement = statement.where(EvaluationResult.run_id == run_id)
    if module:
        statement = statement.where(EvaluationResult.module == module)
    statement = statement.order_by(EvaluationResult.created_at, EvaluationResult.id).limit(
        limit
    )
    return [_to_result_record(result) for result in db.scalars(statement).all()]


def count_evaluation_runs(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(EvaluationRun)) or 0


def count_evaluation_cases(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(EvaluationCase)) or 0


def count_failed_results(db: Session) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(EvaluationResult)
            .where(EvaluationResult.passed.is_(False))
        )
        or 0
    )
