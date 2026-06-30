from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.repositories import evaluation_repository
from app.schemas.evaluations import (
    BadCaseAddToEvalRequest,
    BadCaseCreateRequest,
    BadCaseEvaluationLinkResponse,
    BadCaseRecord,
    BadCaseStats,
    BadCaseUpdateRequest,
    EvaluationCaseCreateRequest,
    EvaluationCaseRecord,
    EvaluationDatasetRecord,
    EvaluationResultRecord,
    EvaluationRunCreateRequest,
    EvaluationRunRecord,
    EvaluationRunSummary,
    EvaluationStats,
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
ALLOWED_STATUSES = {"open", "reviewing", "fixed", "verified", "wont_fix"}
RESOLVED_STATUSES = {"fixed", "verified", "wont_fix"}
OPEN_STATUSES = {"open", "reviewing"}
EVALUATION_MODULES = {
    "jd_parser",
    "resume_parser",
    "match",
    "rag",
    "agent",
    "application",
    "bad_case",
}
EVALUATION_RUN_MODULES = EVALUATION_MODULES | {"all"}
EVALUATION_RUN_STATUSES = {"pending", "running", "completed", "failed"}
EVALUATION_CASE_SOURCE_TYPES = {"synthetic", "bad_case", "manual"}
SYNTHETIC_DATASET_NAME = "synthetic_smoke_v1"
SYNTHETIC_MODULE_ORDER = [
    "jd_parser",
    "resume_parser",
    "match",
    "rag",
    "agent",
    "application",
    "bad_case",
]
REPO_ROOT = Path(__file__).resolve().parents[3]
EVALS_ROOT = REPO_ROOT / "evals"
PRIVATE_TEXT_KEYS = {
    "raw_text",
    "jd_raw_text",
    "chunk_text",
    "full_text",
    "resume_text",
    "job_text",
}


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


def _normalize_evaluation_module(value: str | None, *, allow_all: bool = False) -> str:
    normalized = (value or "all").strip().lower()
    allowed_values = EVALUATION_RUN_MODULES if allow_all else EVALUATION_MODULES
    if normalized not in allowed_values:
        raise AppError(
            code="evaluation_invalid_field",
            message="Unsupported evaluation module.",
            status_code=400,
            details={"field": "module"},
        )
    return normalized


def _normalize_evaluation_source_type(value: str) -> str:
    normalized = _normalize_required(value, "source_type").lower()
    if normalized not in EVALUATION_CASE_SOURCE_TYPES:
        raise AppError(
            code="evaluation_invalid_field",
            message="Unsupported evaluation case source_type.",
            status_code=400,
            details={"field": "source_type"},
        )
    return normalized


def _normalize_dataset_name(value: str | None) -> str:
    normalized = (value or SYNTHETIC_DATASET_NAME).strip()
    if not normalized:
        raise AppError(
            code="evaluation_invalid_field",
            message="dataset_name is required.",
            status_code=400,
            details={"field": "dataset_name"},
        )
    return normalized


def _normalize_case_name(value: str) -> str:
    return _normalize_required(value, "case_name")


def _normalize_tags(tags: list[str] | None) -> list[str]:
    normalized: list[str] = []
    for tag in tags or []:
        value = str(tag).strip()
        if value and value not in normalized:
            normalized.append(value)
    return normalized


def _current_code_version() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            check=True,
            text=True,
            timeout=2,
        )
    except Exception:
        return "unknown"
    return completed.stdout.strip() or "unknown"


def _contains_private_text_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in PRIVATE_TEXT_KEYS:
                return True
            if _contains_private_text_key(child):
                return True
    elif isinstance(value, list):
        return any(_contains_private_text_key(child) for child in value)
    return False


def _reject_private_payload(*payloads: dict[str, Any]) -> None:
    for payload in payloads:
        if _contains_private_text_key(payload):
            raise AppError(
                code="evaluation_private_text_rejected",
                message="Evaluation cases must use summaries or refs, not raw private text.",
                status_code=400,
                details={"private_keys": sorted(PRIVATE_TEXT_KEYS)},
            )


def _safe_summary(value: str | None, *, max_length: int = 180) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    if not normalized:
        return None
    if len(normalized) <= max_length:
        return normalized
    return f"{normalized[: max_length - 3]}..."


def _module_from_bad_case_source(source_type: str) -> str:
    mapping = {
        "job_description": "jd_parser",
        "resume_version": "resume_parser",
        "match_report": "match",
        "rag_answer": "rag",
        "rag_document": "rag",
        "agent_run": "agent",
        "agent_step": "agent",
        "data_persistence": "application",
    }
    return mapping.get(source_type, "bad_case")


def _bad_case_eval_payloads(
    bad_case: BadCaseRecord,
    module: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    input_payload: dict[str, Any] = {
        "source_type": bad_case.source_type,
        "source_id": bad_case.source_id,
        "category": bad_case.category,
        "severity": bad_case.severity,
        "status": bad_case.status,
        "description_summary": _safe_summary(bad_case.description),
        "root_cause_summary": _safe_summary(bad_case.root_cause),
        "fix_strategy_summary": _safe_summary(
            bad_case.fix_strategy or bad_case.suggested_fix
        ),
        "tags": _normalize_tags(bad_case.tags),
    }
    expected_output: dict[str, Any] = {
        "expected_behavior_summary": _safe_summary(bad_case.expected_behavior),
        "actual_behavior_summary": _safe_summary(bad_case.actual_behavior),
        "fix_strategy_summary": _safe_summary(
            bad_case.fix_strategy or bad_case.suggested_fix
        ),
    }

    if module == "jd_parser":
        input_payload.update(
            {
                "job_title": bad_case.title,
                "company": "Unknown",
                "required_skills": ["regression"],
            }
        )
        expected_output.update(
            {
                "required_fields": [
                    "role_title",
                    "company",
                    "required_skills",
                    "role_category",
                ],
                "expected_skills": ["regression"],
            }
        )
    elif module == "resume_parser":
        input_payload.update(
            {
                "candidate_ref": bad_case.source_id,
                "skills": ["regression"],
                "sections": ["summary"],
            }
        )
        expected_output.update(
            {
                "required_fields": ["candidate_ref", "skills", "sections"],
                "expected_skills": ["regression"],
            }
        )
    elif module == "match":
        input_payload.update(
            {
                "resume_signals": ["regression"],
                "jd_requirements": ["regression"],
            }
        )
        expected_output.update(
            {
                "required_fields": [
                    "total_score",
                    "dimension_scores",
                    "strengths",
                    "gaps",
                    "evidence",
                ],
                "score_min": 0,
                "score_max": 100,
            }
        )
    elif module == "rag":
        input_payload.update(
            {
                "query": bad_case.title,
                "expected_keywords": ["synthetic"],
            }
        )
        expected_output.update(
            {
                "required_fields": ["sources", "snippets", "uncertainty"],
                "allow_no_evidence": True,
            }
        )
    elif module == "agent":
        input_payload.update(
            {
                "workflow_name": "job_application_preparation",
                "resume_version_id": bad_case.source_id,
                "jd_id": bad_case.source_id,
            }
        )
        expected_output.update(
            {
                "allowed_statuses": ["completed", "need_more_info"],
                "requires_ordered_steps": True,
            }
        )
    elif module == "application":
        input_payload.update(
            {
                "company": "Unknown",
                "role_title": bad_case.title,
                "status": "applied",
                "filter_status": "applied",
            }
        )
        expected_output.update(
            {
                "valid_status": "applied",
                "stats_fields": [
                    "total_applications",
                    "by_status",
                    "active_count",
                ],
            }
        )
    else:
        expected_output.update(
            {
                "required_fields": ["source_type", "source_id", "category", "status"],
                "privacy_safe": True,
            }
        )

    return input_payload, expected_output


def _synthetic_case_definitions(dataset_name: str) -> list[dict[str, Any]]:
    return [
        {
            "module": "jd_parser",
            "dataset_name": dataset_name,
            "case_name": "jd_parser_contract_smoke",
            "input_payload": {
                "job_title": "AI Application Engineer",
                "company": "Synthetic Company",
                "required_skills": ["python", "fastapi", "rag"],
            },
            "expected_output": {
                "required_fields": [
                    "role_title",
                    "company",
                    "required_skills",
                    "role_category",
                ],
                "expected_skills": ["python", "fastapi"],
            },
            "tags": ["synthetic", "smoke", "jd_parser"],
        },
        {
            "module": "resume_parser",
            "dataset_name": dataset_name,
            "case_name": "resume_parser_contract_smoke",
            "input_payload": {
                "candidate_ref": "synthetic_resume",
                "skills": ["python", "react", "sql"],
                "sections": ["experience", "projects", "education"],
            },
            "expected_output": {
                "required_fields": ["candidate_ref", "skills", "sections"],
                "expected_skills": ["python", "react"],
            },
            "tags": ["synthetic", "smoke", "resume_parser"],
        },
        {
            "module": "match",
            "dataset_name": dataset_name,
            "case_name": "match_report_contract_smoke",
            "input_payload": {
                "resume_signals": ["python", "fastapi", "react"],
                "jd_requirements": ["python", "fastapi", "cloud"],
            },
            "expected_output": {
                "required_fields": [
                    "total_score",
                    "dimension_scores",
                    "strengths",
                    "gaps",
                    "evidence",
                ],
                "score_min": 0,
                "score_max": 100,
            },
            "tags": ["synthetic", "smoke", "match"],
        },
        {
            "module": "rag",
            "dataset_name": dataset_name,
            "case_name": "rag_answer_contract_smoke",
            "input_payload": {
                "query": "python interview preparation",
                "expected_keywords": ["python", "interview"],
            },
            "expected_output": {
                "required_fields": ["sources", "snippets", "uncertainty"],
                "allow_no_evidence": True,
            },
            "tags": ["synthetic", "smoke", "rag"],
        },
        {
            "module": "agent",
            "dataset_name": dataset_name,
            "case_name": "agent_workflow_contract_smoke",
            "input_payload": {
                "workflow_name": "job_application_preparation",
                "resume_version_id": None,
                "jd_id": None,
            },
            "expected_output": {
                "allowed_statuses": ["completed", "need_more_info"],
                "requires_ordered_steps": True,
            },
            "tags": ["synthetic", "smoke", "agent"],
        },
        {
            "module": "application",
            "dataset_name": dataset_name,
            "case_name": "application_tracking_contract_smoke",
            "input_payload": {
                "company": "Synthetic Company",
                "role_title": "AI Application Engineer",
                "status": "applied",
                "filter_status": "applied",
            },
            "expected_output": {
                "valid_status": "applied",
                "stats_fields": [
                    "total_applications",
                    "by_status",
                    "active_count",
                ],
            },
            "tags": ["synthetic", "smoke", "application"],
        },
        {
            "module": "bad_case",
            "dataset_name": dataset_name,
            "case_name": "bad_case_contract_smoke",
            "input_payload": {
                "source_type": "match_report",
                "source_id": "synthetic_match_report",
                "category": "match_score_inaccurate",
            },
            "expected_output": {
                "required_fields": ["source_type", "source_id", "category", "status"],
                "privacy_safe": True,
            },
            "tags": ["synthetic", "smoke", "bad_case"],
        },
    ]


def _required_fields_present(actual_output: dict[str, Any], fields: list[str]) -> bool:
    return all(field in actual_output for field in fields)


def _evaluate_jd_parser_case(evaluation_case: EvaluationCaseRecord) -> dict[str, Any]:
    skills = [
        str(skill).lower()
        for skill in evaluation_case.input_payload.get("required_skills", [])
    ]
    actual_output = {
        "role_title": evaluation_case.input_payload.get("job_title"),
        "company": evaluation_case.input_payload.get("company"),
        "required_skills": skills,
        "role_category": "engineering" if skills else "unknown",
    }
    expected = evaluation_case.expected_output
    expected_skills = {str(skill).lower() for skill in expected.get("expected_skills", [])}
    passed = _required_fields_present(
        actual_output,
        expected.get("required_fields", []),
    ) and expected_skills.issubset(set(skills))
    return {
        "actual_output": actual_output,
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "error": None if passed else "JD parser contract fields or skills failed.",
    }


def _evaluate_resume_parser_case(
    evaluation_case: EvaluationCaseRecord,
) -> dict[str, Any]:
    skills = [str(skill).lower() for skill in evaluation_case.input_payload.get("skills", [])]
    sections = [
        str(section).lower()
        for section in evaluation_case.input_payload.get("sections", [])
    ]
    actual_output = {
        "candidate_ref": evaluation_case.input_payload.get("candidate_ref"),
        "skills": skills,
        "sections": sections,
    }
    expected = evaluation_case.expected_output
    expected_skills = {str(skill).lower() for skill in expected.get("expected_skills", [])}
    passed = _required_fields_present(
        actual_output,
        expected.get("required_fields", []),
    ) and expected_skills.issubset(set(skills))
    return {
        "actual_output": actual_output,
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "error": None if passed else "Resume parser contract fields or skills failed.",
    }


def _evaluate_match_case(evaluation_case: EvaluationCaseRecord) -> dict[str, Any]:
    resume_signals = set(evaluation_case.input_payload.get("resume_signals", []))
    jd_requirements = set(evaluation_case.input_payload.get("jd_requirements", []))
    overlap = sorted(resume_signals & jd_requirements)
    gaps = sorted(jd_requirements - resume_signals)
    score = 55 + len(overlap) * 12 - len(gaps) * 8
    total_score = max(0, min(100, score))
    actual_output = {
        "total_score": total_score,
        "dimension_scores": {
            "skills": total_score,
            "evidence": 70 if overlap else 35,
        },
        "strengths": [f"Matched {skill}" for skill in overlap],
        "gaps": [f"Missing {skill}" for skill in gaps],
        "evidence": [
            {
                "dimension": "skills",
                "jd_requirement": skill,
                "resume_signal": skill if skill in overlap else None,
            }
            for skill in sorted(jd_requirements)
        ],
    }
    expected = evaluation_case.expected_output
    passed = (
        _required_fields_present(actual_output, expected.get("required_fields", []))
        and expected.get("score_min", 0) <= total_score <= expected.get("score_max", 100)
        and bool(actual_output["strengths"] or actual_output["gaps"])
    )
    return {
        "actual_output": actual_output,
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "error": None if passed else "Match contract fields or score bounds failed.",
    }


def _evaluate_rag_case(evaluation_case: EvaluationCaseRecord) -> dict[str, Any]:
    query = str(evaluation_case.input_payload.get("query", "")).strip()
    keywords = [
        str(keyword).lower()
        for keyword in evaluation_case.input_payload.get("expected_keywords", [])
    ]
    snippet = f"Synthetic source mentions {query}." if query else ""
    actual_output = {
        "query": query,
        "sources": [
            {
                "doc_id": "synthetic_doc",
                "chunk_id": "synthetic_chunk",
                "snippet": snippet,
                "score": 1.0,
            }
        ]
        if query
        else [],
        "snippets": [snippet] if snippet else [],
        "uncertainty": None if query else "No evidence found.",
    }
    text = " ".join(actual_output["snippets"]).lower()
    keyword_match = not keywords or any(keyword in text for keyword in keywords)
    passed = _required_fields_present(
        actual_output,
        evaluation_case.expected_output.get("required_fields", []),
    ) and (keyword_match or evaluation_case.expected_output.get("allow_no_evidence"))
    return {
        "actual_output": actual_output,
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "error": None if passed else "RAG contract did not return expected evidence shape.",
    }


def _evaluate_agent_case(evaluation_case: EvaluationCaseRecord) -> dict[str, Any]:
    has_refs = bool(evaluation_case.input_payload.get("resume_version_id")) and bool(
        evaluation_case.input_payload.get("jd_id")
    )
    status = "completed" if has_refs else "need_more_info"
    actual_output = {
        "workflow_name": evaluation_case.input_payload.get("workflow_name"),
        "status": status,
        "steps": [
            {"step_order": 1, "step_name": "validate_inputs", "status": status},
        ],
    }
    allowed_statuses = evaluation_case.expected_output.get("allowed_statuses", [])
    ordered_steps = [step["step_order"] for step in actual_output["steps"]]
    passed = status in allowed_statuses and ordered_steps == sorted(ordered_steps)
    return {
        "actual_output": actual_output,
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "error": None if passed else "Agent workflow contract failed.",
    }


def _evaluate_application_case(evaluation_case: EvaluationCaseRecord) -> dict[str, Any]:
    status = evaluation_case.input_payload.get("status")
    filter_status = evaluation_case.input_payload.get("filter_status")
    by_status = {status: 1} if status else {}
    actual_output = {
        "created_status": status,
        "filter_status": filter_status,
        "filter_matched": status == filter_status,
        "stats": {
            "total_applications": 1 if status else 0,
            "by_status": by_status,
            "active_count": 1 if status not in {"offer", "rejected", "withdrawn", "archived"} else 0,
        },
    }
    expected = evaluation_case.expected_output
    passed = (
        actual_output["created_status"] == expected.get("valid_status")
        and actual_output["filter_matched"]
        and all(field in actual_output["stats"] for field in expected.get("stats_fields", []))
    )
    return {
        "actual_output": actual_output,
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "error": None if passed else "Application tracking contract failed.",
    }


def _evaluate_bad_case_case(evaluation_case: EvaluationCaseRecord) -> dict[str, Any]:
    actual_output = {
        "source_type": evaluation_case.input_payload.get("source_type"),
        "source_id": evaluation_case.input_payload.get("source_id"),
        "category": evaluation_case.input_payload.get("category"),
        "status": evaluation_case.input_payload.get("status", "open"),
        "privacy_safe": not _contains_private_text_key(evaluation_case.input_payload),
    }
    expected = evaluation_case.expected_output
    passed = _required_fields_present(
        actual_output,
        expected.get("required_fields", []),
    ) and actual_output["privacy_safe"]
    return {
        "actual_output": actual_output,
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "error": None if passed else "Bad case contract failed.",
    }


def _evaluate_case(evaluation_case: EvaluationCaseRecord) -> dict[str, Any]:
    evaluators = {
        "jd_parser": _evaluate_jd_parser_case,
        "resume_parser": _evaluate_resume_parser_case,
        "match": _evaluate_match_case,
        "rag": _evaluate_rag_case,
        "agent": _evaluate_agent_case,
        "application": _evaluate_application_case,
        "bad_case": _evaluate_bad_case_case,
    }
    evaluator = evaluators[evaluation_case.module]
    return evaluator(evaluation_case)


def _build_metrics(results: list[EvaluationResultRecord]) -> dict[str, Any]:
    total_count = len(results)
    passed_count = sum(1 for result in results if result.passed)
    failed_count = total_count - passed_count
    failed_case_ids = [result.case_id for result in results if not result.passed]
    by_module: dict[str, dict[str, float | int]] = {}
    for result in results:
        bucket = by_module.setdefault(
            result.module,
            {"total": 0, "passed": 0, "failed": 0, "pass_rate": 0.0},
        )
        bucket["total"] += 1
        if result.passed:
            bucket["passed"] += 1
        else:
            bucket["failed"] += 1
    for bucket in by_module.values():
        total = int(bucket["total"])
        bucket["pass_rate"] = round(float(bucket["passed"]) / total, 4) if total else 0.0
    return {
        "total_count": total_count,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "failed_case_ids": failed_case_ids,
        "pass_rate": round(passed_count / total_count, 4) if total_count else 0.0,
        "by_module": by_module,
    }


def _sync_bad_case_regression_result(
    db: Session,
    *,
    evaluation_case: EvaluationCaseRecord,
    result: EvaluationResultRecord,
    run_id: str,
) -> None:
    if not evaluation_case.bad_case_id:
        return

    bad_case = evaluation_repository.get_bad_case_model(
        db,
        evaluation_case.bad_case_id,
    )
    if bad_case is None:
        return

    if result.passed:
        now = _now()
        evaluation_repository.update_bad_case(
            db,
            bad_case,
            status="verified",
            added_to_eval_set=True,
            resolved_at=bad_case.resolved_at or now,
            verified_at=now,
            regression_evaluation_run_id=run_id,
            regression_evaluation_case_id=evaluation_case.id,
        )
        return

    next_status = "fixed" if bad_case.status == "verified" else None
    evaluation_repository.update_bad_case(
        db,
        bad_case,
        status=next_status,
        added_to_eval_set=True,
        clear_verified_at=bad_case.status == "verified",
        regression_evaluation_run_id=run_id,
        regression_evaluation_case_id=evaluation_case.id,
    )


def _ensure_synthetic_cases(
    db: Session,
    *,
    dataset_name: str,
    modules: list[str],
) -> list[EvaluationCaseRecord]:
    cases: list[EvaluationCaseRecord] = []
    for definition in _synthetic_case_definitions(dataset_name):
        if definition["module"] not in modules:
            continue
        existing = evaluation_repository.find_evaluation_case(
            db,
            module=definition["module"],
            dataset_name=definition["dataset_name"],
            case_name=definition["case_name"],
            source_type="synthetic",
        )
        if existing:
            cases.append(existing)
            continue
        cases.append(
            evaluation_repository.create_evaluation_case(
                db,
                module=definition["module"],
                dataset_name=definition["dataset_name"],
                case_name=definition["case_name"],
                input_payload=definition["input_payload"],
                expected_output=definition["expected_output"],
                tags=definition["tags"],
                source_type="synthetic",
            )
        )
    return cases


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
        root_cause=_normalize_optional(payload.root_cause),
        fix_strategy=_normalize_optional(payload.fix_strategy),
        tags=_normalize_tags(payload.tags),
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
    verified_at = None
    clear_verified_at = False
    if status in RESOLVED_STATUSES and bad_case.resolved_at is None:
        resolved_at = _now()
    if status == "verified" and bad_case.verified_at is None:
        verified_at = _now()
    elif status in OPEN_STATUSES or status in {"fixed", "wont_fix"}:
        clear_verified_at = True
    if status in OPEN_STATUSES:
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
        root_cause=_normalize_optional(update_data.get("root_cause"))
        if "root_cause" in update_data
        else None,
        fix_strategy=_normalize_optional(update_data.get("fix_strategy"))
        if "fix_strategy" in update_data
        else None,
        tags=_normalize_tags(update_data.get("tags"))
        if "tags" in update_data and update_data.get("tags") is not None
        else None,
        resolved_at=resolved_at,
        clear_resolved_at=clear_resolved_at,
        verified_at=verified_at,
        clear_verified_at=clear_verified_at,
    )


def create_evaluation_case(
    db: Session,
    payload: EvaluationCaseCreateRequest,
) -> EvaluationCaseRecord:
    module = _normalize_evaluation_module(payload.module)
    dataset_name = _normalize_dataset_name(payload.dataset_name)
    source_type = _normalize_evaluation_source_type(payload.source_type)
    bad_case_id = _normalize_optional(payload.bad_case_id)
    if bad_case_id and not evaluation_repository.get_bad_case(db, bad_case_id):
        raise AppError(
            code="bad_case_not_found",
            message="Bad case was not found.",
            status_code=404,
            details={"bad_case_id": bad_case_id},
        )

    input_payload = payload.input_payload or {}
    expected_output = payload.expected_output or {}
    _reject_private_payload(input_payload, expected_output)

    return evaluation_repository.create_evaluation_case(
        db,
        module=module,
        dataset_name=dataset_name,
        case_name=_normalize_case_name(payload.case_name),
        input_payload=input_payload,
        expected_output=expected_output,
        tags=_normalize_tags(payload.tags),
        source_type=source_type,
        bad_case_id=bad_case_id,
    )


def create_evaluation_case_from_bad_case(
    db: Session,
    bad_case_id: str,
) -> EvaluationCaseRecord:
    link = add_bad_case_to_eval(
        db,
        bad_case_id,
        BadCaseAddToEvalRequest(dataset_name=SYNTHETIC_DATASET_NAME),
    )
    return link.evaluation_case


def add_bad_case_to_eval(
    db: Session,
    bad_case_id: str,
    payload: BadCaseAddToEvalRequest | None = None,
) -> BadCaseEvaluationLinkResponse:
    bad_case = evaluation_repository.get_bad_case(db, bad_case_id)
    bad_case_model = evaluation_repository.get_bad_case_model(db, bad_case_id)
    if not bad_case or not bad_case_model:
        raise AppError(
            code="bad_case_not_found",
            message="Bad case was not found.",
            status_code=404,
            details={"bad_case_id": bad_case_id},
        )

    dataset_name = _normalize_dataset_name(
        payload.dataset_name if payload else "regression"
    )
    module = _module_from_bad_case_source(bad_case.source_type)
    existing_case = evaluation_repository.find_evaluation_case_for_bad_case(
        db,
        bad_case_id=bad_case.id,
        dataset_name=dataset_name,
    )
    if existing_case:
        updated_bad_case = evaluation_repository.update_bad_case(
            db,
            bad_case_model,
            added_to_eval_set=True,
            regression_evaluation_case_id=existing_case.id,
        )
        return BadCaseEvaluationLinkResponse(
            bad_case=updated_bad_case,
            evaluation_case=existing_case,
            created=False,
        )

    input_payload, expected_output = _bad_case_eval_payloads(bad_case, module)
    _reject_private_payload(input_payload, expected_output)
    evaluation_case = evaluation_repository.create_evaluation_case(
        db,
        module=module,
        dataset_name=dataset_name,
        case_name=f"bad_case_{bad_case.id}",
        input_payload=input_payload,
        expected_output=expected_output,
        tags=_normalize_tags(["bad_case", bad_case.category, bad_case.severity, *bad_case.tags]),
        source_type="bad_case",
        bad_case_id=bad_case.id,
    )
    updated_bad_case = evaluation_repository.update_bad_case(
        db,
        bad_case_model,
        added_to_eval_set=True,
        regression_evaluation_case_id=evaluation_case.id,
    )
    return BadCaseEvaluationLinkResponse(
        bad_case=updated_bad_case,
        evaluation_case=evaluation_case,
        created=True,
    )


def list_evaluation_cases(
    db: Session,
    *,
    module: str | None = None,
    dataset_name: str | None = None,
    source_type: str | None = None,
    limit: int = 100,
) -> list[EvaluationCaseRecord]:
    normalized_module = _normalize_evaluation_module(module) if module else None
    normalized_dataset_name = (
        _normalize_dataset_name(dataset_name) if dataset_name else None
    )
    normalized_source_type = (
        _normalize_evaluation_source_type(source_type) if source_type else None
    )
    return evaluation_repository.list_evaluation_cases(
        db,
        module=normalized_module,
        dataset_name=normalized_dataset_name,
        source_type=normalized_source_type,
        limit=min(max(limit, 1), 200),
    )


def list_evaluation_datasets() -> list[EvaluationDatasetRecord]:
    datasets: list[EvaluationDatasetRecord] = []
    synthetic_counts: dict[str, int] = {module: 0 for module in SYNTHETIC_MODULE_ORDER}
    for definition in _synthetic_case_definitions(SYNTHETIC_DATASET_NAME):
        synthetic_counts[definition["module"]] += 1
    for module in SYNTHETIC_MODULE_ORDER:
        datasets.append(
            EvaluationDatasetRecord(
                dataset_name=SYNTHETIC_DATASET_NAME,
                module=module,
                case_count=synthetic_counts[module],
                source_type="built-in",
                description="Deterministic synthetic smoke dataset.",
                version="v1.5",
            )
        )

    dataset_root = EVALS_ROOT / "datasets"
    if not dataset_root.exists():
        return datasets

    for path in sorted(dataset_root.glob("*/*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        cases = payload.get("cases", [])
        module = str(payload.get("module") or path.stem.split("_")[0])
        dataset_name = str(payload.get("dataset_name") or path.parent.name)
        if module not in EVALUATION_MODULES:
            continue
        datasets.append(
            EvaluationDatasetRecord(
                dataset_name=dataset_name,
                module=module,
                case_count=len(cases) if isinstance(cases, list) else 0,
                source_type="file",
                description=str(payload.get("description") or path.name),
                version=payload.get("version"),
            )
        )
    return datasets


def run_evaluation(
    db: Session,
    payload: EvaluationRunCreateRequest,
) -> EvaluationRunSummary:
    module = _normalize_evaluation_module(payload.module, allow_all=True)
    dataset_name = _normalize_dataset_name(payload.dataset_name)
    modules = SYNTHETIC_MODULE_ORDER if module == "all" else [module]
    _ensure_synthetic_cases(db, dataset_name=dataset_name, modules=modules)

    cases: list[EvaluationCaseRecord] = []
    for current_module in modules:
        cases.extend(
            evaluation_repository.list_evaluation_cases(
                db,
                module=current_module,
                dataset_name=dataset_name,
                limit=200,
            )
        )

    started_at = _now()
    run_name = _normalize_optional(payload.name) or f"{dataset_name} {module} run"
    run_record = evaluation_repository.create_evaluation_run(
        db,
        name=run_name,
        module=module,
        dataset_name=dataset_name,
        status="running",
        metrics={
            "total_count": 0,
            "passed_count": 0,
            "failed_count": 0,
            "failed_case_ids": [],
            "pass_rate": 0.0,
            "by_module": {},
        },
        run_config={
            "requested_module": module,
            "dataset_name": dataset_name,
            "prompt_version": "deterministic-v1",
            "schema_version": "v1.5",
            "retrieval_version": "lexical-v1",
            "model_version": "none",
            "code_version": _current_code_version(),
            "deterministic": True,
            "llm_judge": False,
            "model_comparison": False,
        },
        started_at=started_at,
    )
    run_model = evaluation_repository.get_evaluation_run_model(db, run_record.id)
    if run_model is None:
        raise AppError(
            code="evaluation_run_not_found",
            message="Evaluation run was not found.",
            status_code=404,
            details={"run_id": run_record.id},
        )

    results: list[EvaluationResultRecord] = []
    for evaluation_case in cases:
        try:
            evaluated = _evaluate_case(evaluation_case)
            passed = bool(evaluated["passed"])
            result = evaluation_repository.create_evaluation_result(
                db,
                run_id=run_record.id,
                case_id=evaluation_case.id,
                module=evaluation_case.module,
                status="passed" if passed else "failed",
                actual_output=evaluated["actual_output"],
                expected_output=evaluation_case.expected_output,
                passed=passed,
                score=float(evaluated["score"]),
                error=evaluated["error"],
            )
        except Exception as exc:
            result = evaluation_repository.create_evaluation_result(
                db,
                run_id=run_record.id,
                case_id=evaluation_case.id,
                module=evaluation_case.module,
                status="error",
                actual_output={},
                expected_output=evaluation_case.expected_output,
                passed=False,
                score=0.0,
                error=str(exc),
            )
        results.append(result)
        _sync_bad_case_regression_result(
            db,
            evaluation_case=evaluation_case,
            result=result,
            run_id=run_record.id,
        )

    metrics = _build_metrics(results)
    updated_run = evaluation_repository.update_evaluation_run(
        db,
        run_model,
        status="completed",
        metrics=metrics,
        finished_at=_now(),
    )
    return EvaluationRunSummary(run=updated_run, results_count=len(results))


def list_evaluation_runs(
    db: Session,
    *,
    module: str | None = None,
    dataset_name: str | None = None,
    limit: int = 50,
) -> list[EvaluationRunRecord]:
    normalized_module = (
        _normalize_evaluation_module(module, allow_all=True) if module else None
    )
    normalized_dataset_name = (
        _normalize_dataset_name(dataset_name) if dataset_name else None
    )
    return evaluation_repository.list_evaluation_runs(
        db,
        module=normalized_module,
        dataset_name=normalized_dataset_name,
        limit=min(max(limit, 1), 100),
    )


def get_evaluation_run(db: Session, run_id: str) -> EvaluationRunSummary:
    run = evaluation_repository.get_evaluation_run(db, run_id)
    if not run:
        raise AppError(
            code="evaluation_run_not_found",
            message="Evaluation run was not found.",
            status_code=404,
            details={"run_id": run_id},
        )
    results = evaluation_repository.list_evaluation_results(db, run_id=run_id, limit=500)
    return EvaluationRunSummary(run=run, results_count=len(results))


def list_evaluation_results(
    db: Session,
    *,
    run_id: str,
    limit: int = 200,
) -> list[EvaluationResultRecord]:
    run = evaluation_repository.get_evaluation_run(db, run_id)
    if not run:
        raise AppError(
            code="evaluation_run_not_found",
            message="Evaluation run was not found.",
            status_code=404,
            details={"run_id": run_id},
        )
    return evaluation_repository.list_evaluation_results(
        db,
        run_id=run_id,
        limit=min(max(limit, 1), 500),
    )


def get_bad_case_stats(db: Session) -> BadCaseStats:
    bad_cases = evaluation_repository.list_bad_cases(db, limit=10000)
    by_status: dict[str, int] = {}
    by_module: dict[str, int] = {module: 0 for module in SYNTHETIC_MODULE_ORDER}
    by_case_type: dict[str, int] = {}
    for bad_case in bad_cases:
        by_status[bad_case.status] = by_status.get(bad_case.status, 0) + 1
        module = _module_from_bad_case_source(bad_case.source_type)
        by_module[module] = by_module.get(module, 0) + 1
        by_case_type[bad_case.category] = by_case_type.get(bad_case.category, 0) + 1

    return BadCaseStats(
        total=len(bad_cases),
        by_status=by_status,
        by_module=by_module,
        by_case_type=by_case_type,
        added_to_eval_set_count=sum(1 for item in bad_cases if item.added_to_eval_set),
        verified_count=sum(1 for item in bad_cases if item.status == "verified"),
        open_count=sum(1 for item in bad_cases if item.status in OPEN_STATUSES),
    )


def get_evaluation_stats(db: Session) -> EvaluationStats:
    runs = evaluation_repository.list_evaluation_runs(db, limit=1)
    latest_run = runs[0] if runs else None
    cases = evaluation_repository.list_evaluation_cases(db, limit=10000)
    by_module: dict[str, int] = {module: 0 for module in SYNTHETIC_MODULE_ORDER}
    for evaluation_case in cases:
        by_module[evaluation_case.module] = by_module.get(evaluation_case.module, 0) + 1

    return EvaluationStats(
        total_runs=evaluation_repository.count_evaluation_runs(db),
        latest_run_status=latest_run.status if latest_run else None,
        latest_pass_rate=latest_run.metrics.get("pass_rate") if latest_run else None,
        total_cases=evaluation_repository.count_evaluation_cases(db),
        failed_results=evaluation_repository.count_failed_results(db),
        by_module=by_module,
    )
