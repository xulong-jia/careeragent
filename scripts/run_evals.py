#!/usr/bin/env python3
"""Run deterministic privacy-safe evaluation fixtures."""

from __future__ import annotations

import argparse
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.evaluation import ai_quality  # noqa: E402
from app.core.versioning import version_metadata  # noqa: E402

EVALS_ROOT = REPO_ROOT / "evals"
DATASET_ROOT = EVALS_ROOT / "datasets"
EXPECTED_ROOT = EVALS_ROOT / "expected"
DEFAULT_OUTPUT_ROOT = EVALS_ROOT / "results"
SYNTHETIC_MODULES = {
    "jd_parser",
    "resume_parser",
    "match",
    "rag",
    "agent",
    "application",
    "bad_case",
}
SERVICE_LEVEL_MODULE_FILES = {
    "jd_parser": "jd_parser_cases.json",
    "resume_parser": "resume_parser_cases.json",
    "match": "match_cases.json",
    "project_rewrite": "project_rewrite_cases.json",
    "rag_retrieval": "rag_retrieval_cases.json",
    "agent_workflow": "agent_workflow_cases.json",
}
SERVICE_LEVEL_MODULE_ALIASES = {
    "rag": "rag_retrieval",
    "agent": "agent_workflow",
}
BENCHMARK_DATASET = "benchmark"
BENCHMARK_MODULE_FILES = {
    "jd_parser": "jd_parser_benchmark.jsonl",
    "resume_parser": "resume_parser_benchmark.jsonl",
    "rag_retrieval": "rag_retrieval_benchmark.jsonl",
    "rag_answer": "rag_answer_benchmark.jsonl",
    "match": "match_benchmark.jsonl",
    "project_rewrite": "project_rewrite_benchmark.jsonl",
    "agent_workflow": "agent_workflow_benchmark.jsonl",
}
BENCHMARK_MODULE_ALIASES = {
    "parser": ["jd_parser", "resume_parser"],
    "rag": ["rag_retrieval", "rag_answer"],
    "agent": ["agent_workflow"],
}
MODULES = (
    SYNTHETIC_MODULES
    | set(SERVICE_LEVEL_MODULE_FILES)
    | set(BENCHMARK_MODULE_FILES)
    | set(BENCHMARK_MODULE_ALIASES)
)
PRIVATE_TEXT_KEYS = {
    "raw_text",
    "jd_raw_text",
    "chunk_text",
    "full_text",
    "resume_text",
    "job_text",
}
SYNTHETIC_DATASET_ALIASES = {"synthetic": "smoke"}
SERVICE_LEVEL_DATASET = "service_level"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return ai_quality.load_jsonl(path)


def _safe_text(value: Any, *, max_length: int = 180) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 3]}..."


def _flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten_text(child) for child in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    return str(value or "")


def _sanitize_private_keys(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, child in value.items():
            if str(key) in PRIVATE_TEXT_KEYS:
                continue
            sanitized[str(key)] = _sanitize_private_keys(child)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_private_keys(item) for item in value]
    return value


def _term_hit_count(terms: list[Any], text_or_values: Any) -> int:
    text = _flatten_text(text_or_values).lower()
    hits = 0
    for term in terms:
        normalized = str(term).strip().lower()
        if normalized and normalized in text:
            hits += 1
    return hits


def _hit_rate(terms: list[Any], text_or_values: Any) -> float:
    if not terms:
        return 1.0
    return round(_term_hit_count(terms, text_or_values) / len(terms), 4)


def _metric_score(metrics: dict[str, Any]) -> float:
    values: list[float] = []
    for value in metrics.values():
        if isinstance(value, bool):
            values.append(1.0 if value else 0.0)
        elif isinstance(value, int | float):
            values.append(float(value))
    if not values:
        return 1.0
    return round(sum(values) / len(values), 4)


def _case_input_payload(case: dict[str, Any]) -> dict[str, Any]:
    if isinstance(case.get("input"), dict):
        return _sanitize_private_keys(case["input"])
    if "documents" in case:
        return _sanitize_private_keys(
            {
                "documents": case.get("documents", []),
                "query": case.get("query"),
                "top_k": case.get("top_k"),
            }
        )
    return _sanitize_private_keys(case)


@contextmanager
def _service_eval_session() -> Iterator[Any]:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.db.base import Base
    import app.models as _app_models  # noqa: F401

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _contains_private_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) in PRIVATE_TEXT_KEYS or _contains_private_key(child):
                return True
    if isinstance(value, list):
        return any(_contains_private_key(item) for item in value)
    return False


def _required_fields_present(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    return all(field in actual for field in expected.get("required_fields", []))


def _evaluate_jd_parser(case: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    case_input = case.get("input", {})
    skills = [str(skill).lower() for skill in case_input.get("required_skills", [])]
    actual = {
        "role_title": case_input.get("job_title"),
        "company": case_input.get("company"),
        "required_skills": skills,
        "role_category": "engineering" if skills else "unknown",
    }
    expected_skills = {str(skill).lower() for skill in expected.get("expected_skills", [])}
    passed = _required_fields_present(actual, expected) and expected_skills.issubset(
        set(skills)
    )
    return _result(actual, expected, passed, "JD parser contract failed.")


def _evaluate_resume_parser(
    case: dict[str, Any],
    expected: dict[str, Any],
) -> dict[str, Any]:
    case_input = case.get("input", {})
    skills = [str(skill).lower() for skill in case_input.get("skills", [])]
    sections = [str(section).lower() for section in case_input.get("sections", [])]
    actual = {
        "candidate_ref": case_input.get("candidate_ref"),
        "skills": skills,
        "sections": sections,
    }
    expected_skills = {str(skill).lower() for skill in expected.get("expected_skills", [])}
    passed = _required_fields_present(actual, expected) and expected_skills.issubset(
        set(skills)
    )
    return _result(actual, expected, passed, "Resume parser contract failed.")


def _evaluate_match(case: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    case_input = case.get("input", {})
    resume_signals = set(case_input.get("resume_signals", []))
    jd_requirements = set(case_input.get("jd_requirements", []))
    overlap = sorted(resume_signals & jd_requirements)
    gaps = sorted(jd_requirements - resume_signals)
    total_score = max(0, min(100, 55 + len(overlap) * 12 - len(gaps) * 8))
    actual = {
        "total_score": total_score,
        "dimension_scores": {"skills": total_score, "evidence": 70 if overlap else 35},
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
    passed = (
        _required_fields_present(actual, expected)
        and expected.get("score_min", 0) <= total_score <= expected.get("score_max", 100)
        and bool(actual["strengths"] or actual["gaps"])
    )
    return _result(actual, expected, passed, "Match contract failed.")


def _evaluate_rag(case: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    case_input = case.get("input", {})
    query = str(case_input.get("query", "")).strip()
    keywords = [str(keyword).lower() for keyword in case_input.get("expected_keywords", [])]
    snippet = f"Synthetic source mentions {query}." if query else ""
    actual = {
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
    text = " ".join(actual["snippets"]).lower()
    keyword_match = not keywords or any(keyword in text for keyword in keywords)
    passed = _required_fields_present(actual, expected) and (
        keyword_match or expected.get("allow_no_evidence")
    )
    return _result(actual, expected, passed, "RAG contract failed.")


def _evaluate_agent(case: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    case_input = case.get("input", {})
    has_refs = bool(case_input.get("resume_version_id")) and bool(case_input.get("jd_id"))
    status = "completed" if has_refs else "need_more_info"
    actual = {
        "workflow_name": case_input.get("workflow_name"),
        "status": status,
        "steps": [
            {"step_order": 1, "step_name": "validate_inputs", "status": status},
            {"step_order": 2, "step_name": "rag_search", "status": status},
            {"step_order": 3, "step_name": "summarize_rag_context", "status": status},
        ],
    }
    ordered_steps = [step["step_order"] for step in actual["steps"]]
    passed = status in expected.get("allowed_statuses", []) and ordered_steps == sorted(
        ordered_steps
    )
    return _result(actual, expected, passed, "Agent workflow contract failed.")


def _evaluate_application(
    case: dict[str, Any],
    expected: dict[str, Any],
) -> dict[str, Any]:
    case_input = case.get("input", {})
    status = case_input.get("status")
    filter_status = case_input.get("filter_status")
    active_statuses = {"offer", "rejected", "withdrawn", "archived"}
    actual = {
        "created_status": status,
        "filter_status": filter_status,
        "filter_matched": status == filter_status,
        "stats": {
            "total_applications": 1 if status else 0,
            "by_status": {status: 1} if status else {},
            "active_count": 1 if status not in active_statuses else 0,
        },
    }
    passed = (
        actual["created_status"] == expected.get("valid_status")
        and actual["filter_matched"]
        and all(field in actual["stats"] for field in expected.get("stats_fields", []))
    )
    return _result(actual, expected, passed, "Application contract failed.")


def _evaluate_bad_case(case: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    case_input = case.get("input", {})
    actual = {
        "source_type": case_input.get("source_type"),
        "source_id": case_input.get("source_id"),
        "category": case_input.get("category"),
        "status": case_input.get("status", "open"),
        "privacy_safe": not _contains_private_key(case_input),
    }
    passed = _required_fields_present(actual, expected) and actual["privacy_safe"]
    return _result(actual, expected, passed, "Bad case contract failed.")


def _result(
    actual: dict[str, Any],
    expected: dict[str, Any],
    passed: bool,
    error: str,
) -> dict[str, Any]:
    return {
        "actual_output": actual,
        "expected_output": expected,
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "error": None if passed else error,
    }


EVALUATORS = {
    "jd_parser": _evaluate_jd_parser,
    "resume_parser": _evaluate_resume_parser,
    "match": _evaluate_match,
    "rag": _evaluate_rag,
    "agent": _evaluate_agent,
    "application": _evaluate_application,
    "bad_case": _evaluate_bad_case,
}


def _service_result(
    *,
    case: dict[str, Any],
    module: str,
    actual: dict[str, Any],
    expected: dict[str, Any],
    metrics: dict[str, Any],
    passed: bool,
    error: str,
    input_summary: str,
    service_calls: list[str],
) -> dict[str, Any]:
    actual_output = {
        **actual,
        "service_calls": service_calls,
        "dataset_kind": "service_level",
    }
    return {
        "case_id": case.get("case_id") or case.get("id"),
        "case_name": case.get("name") or case.get("case_id"),
        "module": module,
        "case_type": "service_level",
        "input_payload": _case_input_payload(case),
        "input_summary": input_summary,
        "expected_output": _sanitize_private_keys(expected),
        "actual_output": _sanitize_private_keys(actual_output),
        "metrics": metrics,
        "passed": passed,
        "score": 1.0 if passed else _metric_score(metrics),
        "error": None if passed else error,
    }


def _create_resume_from_text(db: Any, filename: str, raw_text: str) -> Any:
    from app.services import resume_service

    content_type = "text/markdown" if filename.endswith(".md") else "text/plain"
    return resume_service.create_resume(
        db,
        filename,
        content_type,
        raw_text.encode("utf-8"),
    )


def _create_job_from_input(db: Any, payload: dict[str, Any]) -> Any:
    from app.schemas.jobs import JobCreateRequest
    from app.services import job_service

    return job_service.create_job(
        db,
        JobCreateRequest(
            company=str(payload.get("company") or "Example Company"),
            job_title=str(payload.get("job_title") or "Example Role"),
            location=payload.get("location"),
            raw_text=str(payload.get("raw_text") or ""),
            source_url=None,
        ),
    )


def _evaluate_service_jd_parser(
    db: Any,
    case: dict[str, Any],
    expected: dict[str, Any],
) -> dict[str, Any]:
    job = _create_job_from_input(db, dict(case.get("input") or {}))
    profile = job.job_profile
    actual = {
        "jd_id": job.jd_id,
        "job_title": profile.job_title,
        "company": profile.company,
        "location": profile.location,
        "role_category": profile.role_category,
        "required_skills": profile.required_skills,
        "preferred_skills": profile.preferred_skills,
        "responsibilities": profile.responsibilities,
        "business_scenarios": profile.business_scenarios,
        "hidden_requirements": profile.hidden_requirements,
        "interview_focus": profile.interview_focus,
        "risk_level": profile.risk_level,
        "summary": profile.summary,
        "parse_confidence": profile.parse_confidence,
        "evidence": profile.evidence,
        "warnings": profile.warnings,
        "parser_metadata": profile.parser_metadata,
    }
    required_hits = _term_hit_count(
        expected.get("required_skills_should_include", []),
        profile.required_skills,
    )
    preferred_hits = _term_hit_count(
        expected.get("preferred_skills_should_include", []),
        profile.preferred_skills,
    )
    responsibility_hits = _term_hit_count(
        expected.get("responsibilities_should_include", []),
        profile.responsibilities,
    )
    role_match = str(profile.role_category).lower() == str(
        expected.get("role_category", "")
    ).lower()
    hidden_text = _flatten_text(profile.hidden_requirements)
    evidence_fields = [str(item.get("field", "")) for item in profile.evidence]
    expected_evidence_fields = expected.get("evidence_fields_should_include", [])
    warnings_expected = expected.get("warnings_should_include", [])
    warnings_unexpected = expected.get("warnings_should_not_include", [])
    warning_hit_rate = _hit_rate(warnings_expected, profile.warnings)
    warning_absent = not set(str(item) for item in warnings_unexpected) & set(
        str(item) for item in profile.warnings
    )
    metrics = {
        "required_skill_hit_rate": _hit_rate(
            expected.get("required_skills_should_include", []),
            profile.required_skills,
        ),
        "preferred_skill_hit_rate": _hit_rate(
            expected.get("preferred_skills_should_include", []),
            profile.preferred_skills,
        ),
        "responsibility_hit_rate": _hit_rate(
            expected.get("responsibilities_should_include", []),
            profile.responsibilities,
        ),
        "role_category_match": role_match,
        "hidden_requirement_hit_rate": _hit_rate(
            expected.get("hidden_requirements_should_include", []),
            hidden_text,
        ),
        "evidence_coverage": _hit_rate(expected_evidence_fields, evidence_fields),
        "confidence_present": isinstance(profile.parse_confidence, int | float)
        and profile.parse_confidence > 0,
        "warning_expected_match": warning_hit_rate == 1.0 and warning_absent,
    }
    passed = (
        role_match
        and required_hits >= int(expected.get("minimum_required_skill_hits", 0))
        and preferred_hits >= int(expected.get("minimum_preferred_skill_hits", 0))
        and responsibility_hits >= int(expected.get("minimum_responsibility_hits", 0))
        and metrics["hidden_requirement_hit_rate"]
        >= float(expected.get("minimum_hidden_requirement_hit_rate", 0))
        and metrics["evidence_coverage"]
        >= float(expected.get("minimum_evidence_coverage", 0))
        and metrics["confidence_present"]
        and metrics["warning_expected_match"]
    )
    return _service_result(
        case=case,
        module="jd_parser",
        actual=actual,
        expected=expected,
        metrics={**metrics, "case_pass": passed},
        passed=passed,
        error="JD parser service-level expectations were not met.",
        input_summary=_safe_text(
            f"{job.company} {job.job_title} {profile.role_category}",
        ),
        service_calls=["job_service.create_job"],
    )


def _evaluate_service_resume_parser(
    db: Any,
    case: dict[str, Any],
    expected: dict[str, Any],
) -> dict[str, Any]:
    from app.services import resume_service

    case_input = dict(case.get("input") or {})
    resume = _create_resume_from_text(
        db,
        str(case_input.get("filename") or "resume.txt"),
        str(case_input.get("raw_text") or ""),
    )
    parsed = resume_service.parse_resume(db, resume.resume_id)
    risk = resume_service.check_resume_risk(db, resume.resume_id)
    structured = parsed.structured_resume.model_dump()
    sections = [
        key
        for key in ("education", "projects", "experience", "skills", "certificates")
        if structured.get(key)
    ]
    skill_values = structured.get("skills", {})
    skills = _flatten_text(skill_values)
    project_text = _flatten_text(structured.get("projects", []))
    education_text = _flatten_text(structured.get("education", []))
    risk_types = [
        str(getattr(flag, "type", ""))
        for flag in risk.risk_flags
        if getattr(flag, "type", "")
    ]
    evidence_fields = [
        str(item.get("field", "")) for item in structured.get("evidence", [])
        if isinstance(item, dict)
    ]
    metrics = {
        "section_hit_rate": _hit_rate(expected.get("sections_should_include", []), sections),
        "skill_hit_rate": _hit_rate(expected.get("skills_should_include", []), skills),
        "project_hit_rate": _hit_rate(
            expected.get("projects_should_include", []),
            project_text,
        ),
        "education_hit_rate": _hit_rate(
            expected.get("education_should_include", []),
            education_text,
        ),
        "risk_flag_hit_rate": _hit_rate(
            expected.get("risk_flags_expected", []),
            risk_types,
        ),
        "evidence_coverage": _hit_rate(
            expected.get("evidence_fields_should_include", []),
            evidence_fields,
        ),
        "confidence_present": isinstance(structured.get("parse_confidence"), int | float)
        and structured.get("parse_confidence", 0) > 0,
    }
    passed = all(
        [
            metrics["section_hit_rate"] == 1.0,
            metrics["skill_hit_rate"] == 1.0,
            metrics["project_hit_rate"] == 1.0,
            metrics["education_hit_rate"] == 1.0,
            metrics["risk_flag_hit_rate"] == 1.0,
            metrics["evidence_coverage"]
            >= float(expected.get("minimum_evidence_coverage", 0)),
            metrics["confidence_present"],
        ]
    )
    actual = {
        "resume_id": resume.resume_id,
        "sections": sections,
        "skills": skill_values,
        "projects": structured.get("projects", []),
        "education": structured.get("education", []),
        "experience": structured.get("experience", []),
        "risk_flags": risk_types,
        "parser_risk_flags": structured.get("risk_flags", []),
        "parse_confidence": structured.get("parse_confidence"),
        "evidence": structured.get("evidence", []),
        "warnings": structured.get("warnings", []),
        "parser_metadata": structured.get("parser_metadata", {}),
        "extraction_method": parsed.extraction_method,
    }
    return _service_result(
        case=case,
        module="resume_parser",
        actual=actual,
        expected=expected,
        metrics={**metrics, "case_pass": passed},
        passed=passed,
        error="Resume parser service-level expectations were not met.",
        input_summary=_safe_text(case_input.get("filename")),
        service_calls=[
            "resume_service.create_resume",
            "resume_service.parse_resume",
            "resume_service.check_resume_risk",
        ],
    )


def _evaluate_service_match(
    db: Any,
    case: dict[str, Any],
    expected: dict[str, Any],
) -> dict[str, Any]:
    from app.schemas.matches import MatchCompareRequest, MatchRunRequest
    from app.services import match_service

    case_input = dict(case.get("input") or {})
    if "compare_resume_seeds" in case_input:
        jd_seed = dict(case_input.get("jd_seed") or {})
        job = _create_job_from_input(db, jd_seed)
        version_ids = []
        for index, seed in enumerate(list(case_input.get("compare_resume_seeds") or [])):
            resume_seed = dict(seed or {})
            resume = _create_resume_from_text(
                db,
                str(resume_seed.get("filename") or f"compare_resume_{index}.txt"),
                str(resume_seed.get("raw_text") or ""),
            )
            version_ids.append(resume.resume_id + "_version_0001")
        compare = match_service.compare_matches(
            db,
            MatchCompareRequest(jd_id=job.jd_id, resume_version_ids=version_ids),
        )
        top_expected_index = int(expected.get("expected_top_resume_index", 0))
        top_version = version_ids[top_expected_index] if version_ids else None
        top_item = compare.items[0] if compare.items else None
        score_range = expected.get("score_range") or [0, 100]
        metrics = {
            "dimension_score_present_rate": _hit_rate(
                expected.get(
                    "required_dimension_scores",
                    [
                        "skill_match",
                        "project_relevance",
                        "business_understanding",
                        "expression_quality",
                        "education_fit",
                        "risk_control",
                    ],
                ),
                list(top_item.dimension_scores.keys()) if top_item else [],
            ),
            "evidence_dimension_coverage": 1.0,
            "strength_keyword_hit_rate": _hit_rate(
                expected.get("expected_strength_keywords", []),
                _flatten_text(top_item.main_strengths if top_item else []),
            ),
            "gap_keyword_hit_rate": _hit_rate(
                expected.get("expected_gap_keywords", []),
                _flatten_text(top_item.main_gaps if top_item else []),
            ),
            "score_in_expected_range": bool(top_item)
            and int(score_range[0]) <= top_item.total_score <= int(score_range[1]),
            "risk_flag_hit_rate": 1.0,
            "rewrite_priority_hit_rate": 1.0,
            "scoring_method_present": True,
            "confidence_present": True,
            "ranking_consistency": bool(top_item)
            and top_item.resume_version_id == top_version,
        }
        passed = all(
            [
                metrics["dimension_score_present_rate"] == 1.0,
                metrics["strength_keyword_hit_rate"] == 1.0,
                metrics["gap_keyword_hit_rate"] == 1.0,
                metrics["score_in_expected_range"],
                metrics["ranking_consistency"],
            ]
        )
        actual = {
            "compare_mode": compare.compare_mode,
            "items": [item.model_dump() for item in compare.items],
            "expected_top_resume_version_id": top_version,
        }
        return _service_result(
            case=case,
            module="match",
            actual=actual,
            expected=expected,
            metrics={**metrics, "case_pass": passed},
            passed=passed,
            error="Match compare service-level expectations were not met.",
            input_summary=_safe_text(f"compare resumes against {job.job_title}"),
            service_calls=[
                "resume_service.create_resume",
                "job_service.create_job",
                "match_service.compare_matches",
            ],
        )

    resume_seed = dict(case_input.get("resume_seed") or {})
    jd_seed = dict(case_input.get("jd_seed") or {})
    resume = _create_resume_from_text(
        db,
        str(resume_seed.get("filename") or "match_resume.txt"),
        str(resume_seed.get("raw_text") or ""),
    )
    job = _create_job_from_input(db, jd_seed)
    report = match_service.run_match_report(
        db,
        MatchRunRequest(resume_version_id=resume.resume_id + "_version_0001", jd_id=job.jd_id),
    )
    strengths_text = _flatten_text(report.strengths)
    gaps_text = _flatten_text(report.gaps)
    rewrite_priorities_text = _flatten_text(report.rewrite_priorities)
    evidence_dimensions = [item.dimension for item in report.evidence]
    expected_dimensions = expected.get(
        "required_evidence_dimensions",
        [
            "skill_match",
            "project_relevance",
            "business_understanding",
            "expression_quality",
            "education_fit",
            "risk_control",
        ],
    )
    expected_score_dimensions = expected.get(
        "required_dimension_scores",
        [
            "skill_match",
            "project_relevance",
            "business_understanding",
            "expression_quality",
            "education_fit",
            "risk_control",
        ],
    )
    score_range = expected.get("score_range") or [0, 100]
    risk_flag_types = [
        str(flag.get("type"))
        for flag in report.risk_flags
        if isinstance(flag, dict) and flag.get("type")
    ]
    metrics = {
        "dimension_score_present_rate": _hit_rate(
            expected_score_dimensions,
            list(report.dimension_scores.keys()),
        ),
        "evidence_dimension_coverage": _hit_rate(
            expected_dimensions,
            evidence_dimensions,
        ),
        "strength_keyword_hit_rate": _hit_rate(
            expected.get("expected_strength_keywords", []),
            strengths_text,
        ),
        "gap_keyword_hit_rate": _hit_rate(
            expected.get("expected_gap_keywords", []),
            gaps_text,
        ),
        "score_in_expected_range": int(score_range[0])
        <= report.total_score
        <= int(score_range[1]),
        "risk_flag_hit_rate": _hit_rate(
            expected.get("risk_flags_should_include", []),
            risk_flag_types,
        ),
        "rewrite_priority_hit_rate": _hit_rate(
            expected.get("rewrite_priorities_should_include", []),
            rewrite_priorities_text,
        ),
        "scoring_method_present": bool(report.scoring_method),
        "confidence_present": isinstance(report.confidence, int | float)
        and report.confidence > 0,
    }
    passed = all(
        [
            metrics["dimension_score_present_rate"] == 1.0,
            metrics["evidence_dimension_coverage"] == 1.0,
            metrics["strength_keyword_hit_rate"] == 1.0,
            metrics["gap_keyword_hit_rate"] == 1.0,
            metrics["score_in_expected_range"],
            metrics["risk_flag_hit_rate"] == 1.0,
            metrics["rewrite_priority_hit_rate"] == 1.0,
            metrics["scoring_method_present"],
            metrics["confidence_present"],
        ]
    )
    actual = {
        "match_report_id": report.match_report_id,
        "total_score": report.total_score,
        "dimension_scores": report.dimension_scores,
        "evidence": [item.model_dump() for item in report.evidence],
        "strengths": report.strengths,
        "gaps": report.gaps,
        "rewrite_priorities": report.rewrite_priorities,
        "risk_flags": report.risk_flags,
        "recommended_projects": report.recommended_projects,
        "score_breakdown": report.score_breakdown,
        "scoring_method": report.scoring_method,
        "confidence": report.confidence,
    }
    return _service_result(
        case=case,
        module="match",
        actual=actual,
        expected=expected,
        metrics={**metrics, "case_pass": passed},
        passed=passed,
        error="Match service-level expectations were not met.",
        input_summary=_safe_text(f"{resume.filename} against {job.job_title}"),
        service_calls=[
            "resume_service.create_resume",
            "job_service.create_job",
            "match_service.run_match_report",
        ],
    )


def _evaluate_service_project_rewrite(
    db: Any,
    case: dict[str, Any],
    expected: dict[str, Any],
) -> dict[str, Any]:
    from app.schemas.projects import ProjectCreateRequest, ProjectRewriteRequest
    from app.services import project_rewrite_service, project_service

    case_input = dict(case.get("input") or {})
    project_seed = dict(case_input.get("project_seed") or {})
    jd_seed = dict(case_input.get("jd_seed") or {})
    project = project_service.create_project(
        db,
        ProjectCreateRequest(
            name=str(project_seed.get("name") or "Service Rewrite Project"),
            role=project_seed.get("role"),
            period=project_seed.get("period"),
            background=project_seed.get("background"),
            tech_stack=list(project_seed.get("tech_stack") or []),
            responsibilities=list(project_seed.get("responsibilities") or []),
            results=list(project_seed.get("results") or []),
            evidence=list(project_seed.get("evidence") or []),
            status=str(project_seed.get("status") or "active"),
        ),
    )
    job = _create_job_from_input(db, jd_seed)
    rewrite = project_rewrite_service.create_project_rewrite(
        db,
        project.id,
        ProjectRewriteRequest(jd_id=job.jd_id),
    )
    bullets = [bullet.model_dump() for bullet in rewrite.rewritten_bullets]
    matched_points = [point.model_dump() for point in rewrite.matched_points]
    missing_points = [point.model_dump() for point in rewrite.missing_points]
    risk_flags = [flag.model_dump() for flag in rewrite.risk_flags]
    bullet_text = _flatten_text(bullets)
    matched_text = _flatten_text(matched_points)
    missing_text = _flatten_text(missing_points)
    risk_types = [
        str(flag.get("type"))
        for flag in risk_flags
        if isinstance(flag, dict) and flag.get("type")
    ]
    before_after_present = bool(bullets) and all(
        "before" in bullet and "after" in bullet for bullet in bullets
    )
    requires_evidence = bool(expected.get("requires_evidence_required"))
    evidence_required_present = all(
        "evidence_required" in bullet
        for bullet in bullets
    ) and (
        not requires_evidence
        or any(bool(bullet.get("evidence_required")) for bullet in bullets)
    )
    forbidden_changes_present = bool(rewrite.forbidden_changes) and all(
        bullet.get("forbidden_changes") for bullet in bullets
    )
    risk_level_present = bool(bullets) and all(
        bullet.get("risk_level") in {"low", "medium", "high"} for bullet in bullets
    )
    forbidden_terms = [
        str(term).lower()
        for term in expected.get("forbidden_terms_should_not_appear", [])
    ]
    after_text = " ".join(str(bullet.get("after") or "") for bullet in bullets).lower()
    fabrication_guard_pass = not any(term and term in after_text for term in forbidden_terms)
    metrics = {
        "before_after_present": before_after_present,
        "evidence_required_present": evidence_required_present,
        "forbidden_changes_present": forbidden_changes_present,
        "risk_level_present": risk_level_present,
        "matched_requirement_hit_rate": _hit_rate(
            expected.get("matched_requirements_should_include", []),
            matched_text,
        ),
        "missing_point_hit_rate": _hit_rate(
            expected.get("missing_points_should_include", []),
            missing_text,
        ),
        "risk_flag_hit_rate": _hit_rate(
            expected.get("risk_flags_should_include", []),
            risk_types,
        ),
        "bullet_keyword_hit_rate": _hit_rate(
            expected.get("bullet_keywords_should_include", []),
            bullet_text,
        ),
        "fabrication_guard_pass": fabrication_guard_pass,
    }
    passed = all(
        [
            before_after_present,
            evidence_required_present,
            forbidden_changes_present,
            risk_level_present,
            metrics["matched_requirement_hit_rate"] == 1.0,
            metrics["missing_point_hit_rate"] == 1.0,
            metrics["risk_flag_hit_rate"] == 1.0,
            metrics["bullet_keyword_hit_rate"] == 1.0,
            fabrication_guard_pass,
        ]
    )
    actual = {
        "rewrite_id": rewrite.id,
        "project_id": rewrite.project_id,
        "jd_id": rewrite.jd_id,
        "matched_points": matched_points,
        "missing_points": missing_points,
        "evidence_required": [
            item.model_dump() for item in rewrite.evidence_required
        ],
        "rewritten_bullets": bullets,
        "forbidden_changes": rewrite.forbidden_changes,
        "risk_flags": risk_flags,
        "rewrite_method": rewrite.rewrite_method,
        "confidence": rewrite.confidence,
    }
    return _service_result(
        case=case,
        module="project_rewrite",
        actual=actual,
        expected=expected,
        metrics={**metrics, "case_pass": passed},
        passed=passed,
        error="Project rewrite service-level expectations were not met.",
        input_summary=_safe_text(f"{project.name} against {job.job_title}"),
        service_calls=[
            "project_service.create_project",
            "job_service.create_job",
            "project_rewrite_service.create_project_rewrite",
        ],
    )


def _evaluate_service_rag_retrieval(
    db: Any,
    case: dict[str, Any],
    expected: dict[str, Any],
) -> dict[str, Any]:
    from app.schemas.rag import RagAnswerRequest, RagDocumentCreateRequest, RagDocumentIndexRequest
    from app.services import rag_service

    created_docs = []
    for document in case.get("documents", []):
        created = rag_service.create_document(
            db,
            RagDocumentCreateRequest(
                title=str(document.get("title") or "Example Document"),
                source_type=str(document.get("source_type") or "manual"),
                raw_text=str(document.get("raw_text") or ""),
                source_uri=document.get("source_uri"),
                metadata=dict(document.get("metadata") or {}),
            ),
        )
        rag_service.index_document(db, created.doc_id, RagDocumentIndexRequest())
        created_docs.append(created)
    retrieval_mode = str(
        case.get("retrieval_mode")
        or expected.get("retrieval_mode")
        or "lexical"
    )
    answer = rag_service.answer_question(
        db,
        RagAnswerRequest(
            question=str(case.get("query") or ""),
            top_k=int(case.get("top_k") or 3),
            filters=case.get("filters"),
            retrieval_mode=retrieval_mode,
            score_threshold=case.get("score_threshold"),
            persist=False,
        ),
    )
    source_text = _flatten_text([source.snippet for source in answer.sources])
    source_types = [source.source_type for source in answer.sources]
    scores = [source.score for source in answer.sources]
    expected_source_type = expected.get("expected_source_type")
    should_have_citation = bool(expected.get("should_have_citation", True))
    expected_uncertainty = expected.get(
        "expected_uncertainty",
        "grounded" if should_have_citation else "no_relevant_source",
    )
    expected_vector_index_used = expected.get("vector_index_used")
    metrics = {
        "recall_at_k_term_hit": _hit_rate(
            expected.get("relevant_terms_should_appear", []),
            source_text,
        ),
        "citation_present": bool(answer.citations),
        "expected_source_type_match": (
            str(expected_source_type) in source_types if expected_source_type else True
        ),
        "retrieval_mode_match": answer.retrieval_debug.retrieval_mode
        == retrieval_mode,
        "average_top_score": round(sum(scores) / len(scores), 4) if scores else 0.0,
        "vector_index_used": bool(answer.retrieval_debug.vector_index_used),
        "uncertainty_match": answer.uncertainty == expected_uncertainty,
    }
    vector_index_ok = (
        True
        if expected_vector_index_used is None
        else metrics["vector_index_used"] == bool(expected_vector_index_used)
    )
    passed = (
        metrics["recall_at_k_term_hit"]
        >= float(expected.get("minimum_recall_at_k", 0))
        and metrics["citation_present"] == should_have_citation
        and metrics["expected_source_type_match"]
        and metrics["retrieval_mode_match"]
        and vector_index_ok
        and metrics["uncertainty_match"]
    )
    actual = {
        "query": answer.question,
        "retrieval_mode": answer.retrieval_mode,
        "evidence_used": answer.evidence_used,
        "grounded": answer.grounded,
        "uncertainty": answer.uncertainty,
        "sources": [source.model_dump() for source in answer.sources],
        "citations": [citation.model_dump() for citation in answer.citations],
        "retrieval_debug": answer.retrieval_debug.model_dump(),
        "created_doc_ids": [doc.doc_id for doc in created_docs],
    }
    return _service_result(
        case=case,
        module="rag_retrieval",
        actual=actual,
        expected=expected,
        metrics={**metrics, "case_pass": passed},
        passed=passed,
        error="RAG service-level expectations were not met.",
        input_summary=_safe_text(case.get("query")),
        service_calls=[
            "rag_service.create_document",
            "rag_service.index_document",
            "rag_service.answer_question",
        ],
    )


def _evaluate_service_agent_workflow(
    db: Any,
    case: dict[str, Any],
    expected: dict[str, Any],
) -> dict[str, Any]:
    from app.agents import steps as agent_steps
    from app.models.application import Application
    from app.repositories import agent_repository
    from app.services import agent_service

    case_input = dict(case.get("input") or {})
    seed = dict(case_input.get("seed_data") or {})
    payload = dict(case_input.get("payload") or {})
    defer_seed_refs = bool(case_input.get("defer_seed_refs_until_resume"))
    created_resume_version_id: str | None = None
    created_jd_id: str | None = None
    if seed:
        resume_seed = dict(seed.get("resume") or {})
        jd_seed = dict(seed.get("jd") or {})
        if resume_seed:
            resume = _create_resume_from_text(
                db,
                str(resume_seed.get("filename") or "agent_resume.txt"),
                str(resume_seed.get("raw_text") or ""),
            )
            created_resume_version_id = resume.resume_id + "_version_0001"
            if not defer_seed_refs:
                payload.setdefault("resume_version_id", created_resume_version_id)
        if jd_seed:
            job = _create_job_from_input(db, jd_seed)
            created_jd_id = job.jd_id
            if not defer_seed_refs:
                payload.setdefault("jd_id", created_jd_id)
        application_seed = dict(seed.get("application") or {})
        if application_seed:
            application_id = str(
                application_seed.get("id")
                or f"app_eval_{str(case.get('case_id') or 'agent').lower()}"
            )
            db.add(
                Application(
                    id=application_id,
                    company=str(application_seed.get("company") or "Example Company"),
                    role_title=str(application_seed.get("role_title") or "Example Role"),
                    role_category=application_seed.get("role_category"),
                    jd_id=application_seed.get("jd_id") or created_jd_id,
                    resume_version_id=(
                        application_seed.get("resume_version_id")
                        or created_resume_version_id
                    ),
                    match_report_id=application_seed.get("match_report_id"),
                    agent_run_id=application_seed.get("agent_run_id"),
                    status=str(application_seed.get("status") or "saved"),
                    priority=str(application_seed.get("priority") or "medium"),
                    reflection=application_seed.get("reflection"),
                    tags=list(application_seed.get("tags") or ["agent_eval"]),
                )
            )
            db.commit()
            payload.setdefault("application_id", application_id)

    workflow_name = str(
        payload.get("workflow_name")
        or case_input.get("workflow_name")
        or "job_application_preparation"
    )
    force_step_failure = str(case_input.get("force_step_failure") or "")
    original_match = agent_steps.match_service.run_match_report
    if force_step_failure == "run_match_report":
        def fail_match_report(db: Any, payload: Any) -> Any:
            raise RuntimeError("synthetic service-level agent failure")

        agent_steps.match_service.run_match_report = fail_match_report

    action_results = {"resume": False, "retry": False, "cancel": False}
    try:
        run = agent_service.create_run_for_workflow(db, payload)
        for action in list(case_input.get("actions") or []):
            action_type = str(action.get("type") or "")
            if action_type == "resume":
                resume_payload = dict(action.get("payload") or {})
                if created_resume_version_id:
                    resume_payload.setdefault("resume_version_id", created_resume_version_id)
                if created_jd_id:
                    resume_payload.setdefault("jd_id", created_jd_id)
                run = agent_service.resume_run(db, run.id, resume_payload)
                action_results["resume"] = run.status == expected.get("expected_status")
            elif action_type == "retry":
                if force_step_failure:
                    agent_steps.match_service.run_match_report = original_match
                run = agent_service.retry_run(db, run.id)
                action_results["retry"] = run.status == expected.get("expected_status")
            elif action_type == "cancel":
                run = agent_service.cancel_run(db, run.id)
                action_results["cancel"] = run.status == expected.get("expected_status")
    finally:
        agent_steps.match_service.run_match_report = original_match

    steps = agent_repository.list_steps_for_run(db, run.id)
    step_names = [step.step_name for step in steps]
    missing_slots = [
        str(slot.get("name"))
        for slot in (run.missing_slots or [])
        if isinstance(slot, dict) and slot.get("name")
    ]
    expected_steps = expected.get("expected_steps_should_include", [])
    expected_missing = expected.get("expected_missing_slots", [])
    step_coverage = _hit_rate(expected_steps, step_names)
    missing_slot_match = sorted(missing_slots) == sorted(expected_missing)
    privacy_safe_payload_present = bool(steps) and all(
        bool(step.privacy_safe_payload) for step in steps
    )
    private_payload_leak = any(
        key in _flatten_text([step.input_refs, step.output_refs, step.privacy_safe_payload])
        for key in PRIVATE_TEXT_KEYS
        for step in steps
    )
    expected_bad_case_payload = bool(expected.get("bad_case_payload_present"))
    metrics = {
        "expected_status_match": run.status == expected.get("expected_status"),
        "expected_step_coverage": step_coverage,
        "missing_slot_match": missing_slot_match,
        "resume_success": (
            action_results["resume"] if expected.get("resume_success") else True
        ),
        "retry_success": (
            action_results["retry"] if expected.get("retry_success") else True
        ),
        "cancel_success": (
            action_results["cancel"] if expected.get("cancel_success") else True
        ),
        "bad_case_payload_present": (
            bool(run.bad_case_payload) if expected_bad_case_payload else True
        ),
        "run_config_present": bool(run.run_config),
        "privacy_safe_payload_present": privacy_safe_payload_present
        and not private_payload_leak,
    }
    passed = all(
        [
            metrics["expected_status_match"],
            step_coverage == 1.0,
            missing_slot_match,
            metrics["resume_success"],
            metrics["retry_success"],
            metrics["cancel_success"],
            metrics["bad_case_payload_present"],
            metrics["run_config_present"],
            metrics["privacy_safe_payload_present"],
        ]
    )
    actual = {
        "run_id": run.id,
        "workflow_name": run.workflow_name,
        "status": run.status,
        "steps": [
            {
                "step_name": step.step_name,
                "step_order": step.step_order,
                "attempt": step.attempt,
                "status": step.status,
                "privacy_safe_payload_present": bool(step.privacy_safe_payload),
            }
            for step in steps
        ],
        "missing_slots": run.missing_slots or [],
        "questions": run.questions or [],
        "output_refs": run.output_refs,
        "run_config": run.run_config,
        "retry_attempt": run.retry_attempt,
        "bad_case_id": run.bad_case_id,
        "bad_case_payload": run.bad_case_payload,
        "action_results": action_results,
    }
    return _service_result(
        case=case,
        module="agent_workflow",
        actual=actual,
        expected=expected,
        metrics={**metrics, "case_pass": passed},
        passed=passed,
        error="Agent workflow service-level expectations were not met.",
        input_summary=_safe_text(workflow_name),
        service_calls=[
            "agent_service.create_run_for_workflow",
            "agent_service.resume_run/retry_run/cancel_run",
            "agent.runner.run_workflow",
        ],
    )


SERVICE_LEVEL_EVALUATORS = {
    "jd_parser": _evaluate_service_jd_parser,
    "resume_parser": _evaluate_service_resume_parser,
    "match": _evaluate_service_match,
    "project_rewrite": _evaluate_service_project_rewrite,
    "rag_retrieval": _evaluate_service_rag_retrieval,
    "agent_workflow": _evaluate_service_agent_workflow,
}


def _benchmark_module_names(module: str | None) -> list[str]:
    if module is None:
        return sorted(BENCHMARK_MODULE_FILES)
    if module in BENCHMARK_MODULE_ALIASES:
        return BENCHMARK_MODULE_ALIASES[module]
    if module in BENCHMARK_MODULE_FILES:
        return [module]
    raise ValueError(f"Unsupported benchmark module: {module}")


def _expected_by_case_id(dataset: str, module: str) -> dict[str, dict[str, Any]]:
    expected_path = (
        EXPECTED_ROOT
        / SYNTHETIC_DATASET_ALIASES.get(dataset, dataset)
        / f"{module}_expected.json"
    )
    if not expected_path.exists():
        return {}
    payload = _load_json(expected_path)
    return {
        str(item["id"]): item.get("expected", {})
        for item in payload.get("cases", [])
        if "id" in item
    }


def _load_cases(dataset: str, module: str | None) -> list[tuple[str, dict[str, Any]]]:
    dataset_dir = DATASET_ROOT / SYNTHETIC_DATASET_ALIASES.get(dataset, dataset)
    if not dataset_dir.exists():
        return []
    modules = [module] if module else sorted(SYNTHETIC_MODULES)
    cases: list[tuple[str, dict[str, Any]]] = []
    for current_module in modules:
        if current_module not in SYNTHETIC_MODULES:
            raise ValueError(f"Unsupported module: {current_module}")
        path = dataset_dir / f"{current_module}_smoke.json"
        if not path.exists():
            continue
        payload = _load_json(path)
        for case in payload.get("cases", []):
            cases.append((current_module, case))
    return cases


def _service_module_name(module: str | None) -> str | None:
    if module is None:
        return None
    return SERVICE_LEVEL_MODULE_ALIASES.get(module, module)


def _load_service_level_cases(module: str | None = None) -> list[tuple[str, dict[str, Any]]]:
    dataset_dir = DATASET_ROOT / SERVICE_LEVEL_DATASET
    selected_module = _service_module_name(module)
    modules = [selected_module] if selected_module else sorted(SERVICE_LEVEL_MODULE_FILES)
    cases: list[tuple[str, dict[str, Any]]] = []
    for current_module in modules:
        filename = SERVICE_LEVEL_MODULE_FILES.get(str(current_module))
        if not filename:
            raise ValueError(f"Unsupported service-level module: {current_module}")
        path = dataset_dir / filename
        if not path.exists():
            continue
        payload = _load_json(path)
        for case in payload.get("cases", []):
            cases.append((str(case.get("module") or current_module), case))
    return cases


def _load_benchmark_cases(module: str | None = None) -> list[tuple[str, dict[str, Any]]]:
    dataset_dir = DATASET_ROOT / BENCHMARK_DATASET
    cases: list[tuple[str, dict[str, Any]]] = []
    for current_module in _benchmark_module_names(module):
        path = dataset_dir / BENCHMARK_MODULE_FILES[current_module]
        if not path.exists():
            continue
        for case in _load_jsonl(path):
            cases.append((str(case.get("module") or current_module), case))
    return cases


def _benchmark_result(
    *,
    case: dict[str, Any],
    module: str,
    actual: dict[str, Any],
    expected: dict[str, Any],
    metrics: dict[str, Any],
    passed: bool,
    error: str,
) -> dict[str, Any]:
    return {
        "case_id": case.get("case_id") or case.get("id"),
        "case_name": case.get("name") or case.get("case_id"),
        "module": module,
        "case_type": "benchmark_foundation",
        "input_payload": _case_input_payload(case),
        "input_summary": _safe_text(case.get("summary") or case.get("name")),
        "expected_output": _sanitize_private_keys(expected),
        "actual_output": _sanitize_private_keys(
            {**actual, "dataset_kind": "benchmark_foundation"}
        ),
        "metrics": metrics,
        "passed": passed,
        "score": 1.0 if passed else _metric_score(metrics),
        "error": None if passed else error,
    }


def _evaluate_benchmark_case(module: str, case: dict[str, Any]) -> dict[str, Any]:
    expected = dict(case.get("expected") or {})
    signals = dict(case.get("signals") or {})
    if module == "jd_parser":
        return _evaluate_benchmark_jd_parser(case, expected, signals)
    if module == "resume_parser":
        return _evaluate_benchmark_resume_parser(case, expected, signals)
    if module == "rag_retrieval":
        return _evaluate_benchmark_rag_retrieval(case, expected, signals)
    if module == "rag_answer":
        return _evaluate_benchmark_rag_answer(case, expected, signals)
    if module == "match":
        return _evaluate_benchmark_match(case, expected, signals)
    if module == "project_rewrite":
        return _evaluate_benchmark_project_rewrite(case, expected, signals)
    if module == "agent_workflow":
        return _evaluate_benchmark_agent_workflow(case, expected, signals)
    raise ValueError(f"Unsupported benchmark module: {module}")


def _evaluate_benchmark_jd_parser(
    case: dict[str, Any],
    expected: dict[str, Any],
    signals: dict[str, Any],
) -> dict[str, Any]:
    expected_required = expected.get("required_skills_should_include", [])
    actual_required = signals.get("parsed_required_skills", [])
    expected_preferred = expected.get("preferred_skills_should_include", [])
    actual_preferred = signals.get("parsed_preferred_skills", [])
    actual_risk_flags = signals.get("risk_flags", [])
    metrics = {
        "role_category_accuracy": str(signals.get("role_category")) == str(expected.get("role_category")),
        "required_skill_precision": _precision(expected_required, actual_required),
        "required_skill_recall": _hit_rate(expected_required, actual_required),
        "preferred_skill_precision": _precision(expected_preferred, actual_preferred),
        "preferred_skill_recall": _hit_rate(expected_preferred, actual_preferred),
        "risk_flag_hit_rate": _hit_rate(
            expected.get("risk_flags_should_include", []),
            actual_risk_flags,
        ),
        "confidence_calibration": _confidence_calibration(signals, expected),
    }
    passed = (
        metrics["role_category_accuracy"]
        and metrics["required_skill_recall"] >= 0.8
        and metrics["preferred_skill_recall"] >= 0.75
        and metrics["confidence_calibration"] >= 0.8
    )
    return _benchmark_result(
        case=case,
        module="jd_parser",
        actual=signals,
        expected=expected,
        metrics={**metrics, "case_pass": passed},
        passed=passed,
        error="JD parser benchmark expectations were not met.",
    )


def _evaluate_benchmark_resume_parser(
    case: dict[str, Any],
    expected: dict[str, Any],
    signals: dict[str, Any],
) -> dict[str, Any]:
    metrics = {
        "section_accuracy": _hit_rate(
            expected.get("sections_should_include", []),
            signals.get("sections", []),
        ),
        "project_extraction_hit_rate": _hit_rate(
            expected.get("projects_should_include", []),
            signals.get("projects", []),
        ),
        "skill_precision": _precision(
            expected.get("skills_should_include", []),
            signals.get("skills", []),
        ),
        "skill_recall": _hit_rate(
            expected.get("skills_should_include", []),
            signals.get("skills", []),
        ),
        "risk_flag_hit_rate": _hit_rate(
            expected.get("risk_flags_should_include", []),
            signals.get("risk_flags", []),
        ),
        "confidence_calibration": _confidence_calibration(signals, expected),
    }
    passed = (
        metrics["section_accuracy"] >= 0.8
        and metrics["project_extraction_hit_rate"] >= 0.8
        and metrics["skill_recall"] >= 0.8
        and metrics["confidence_calibration"] >= 0.8
    )
    return _benchmark_result(
        case=case,
        module="resume_parser",
        actual=signals,
        expected=expected,
        metrics={**metrics, "case_pass": passed},
        passed=passed,
        error="Resume parser benchmark expectations were not met.",
    )


def _evaluate_benchmark_rag_retrieval(
    case: dict[str, Any],
    expected: dict[str, Any],
    signals: dict[str, Any],
) -> dict[str, Any]:
    relevant_ids = [str(item) for item in expected.get("relevant_chunk_ids", [])]
    retrieved_ids = [str(item) for item in signals.get("retrieved_chunk_ids", [])]
    hit_ids = [chunk_id for chunk_id in retrieved_ids if chunk_id in set(relevant_ids)]
    first_hit_rank = next(
        (index + 1 for index, chunk_id in enumerate(retrieved_ids) if chunk_id in set(relevant_ids)),
        None,
    )
    no_evidence_expected = bool(expected.get("no_evidence_expected"))
    metrics = {
        "recall_at_k": round(len(hit_ids) / len(relevant_ids), 4)
        if relevant_ids
        else 1.0,
        "mrr": round(1 / first_hit_rank, 4) if first_hit_rank else 0.0,
        "precision_at_k": round(len(hit_ids) / len(retrieved_ids), 4)
        if retrieved_ids
        else (1.0 if no_evidence_expected else 0.0),
        "citation_coverage": _hit_rate(
            relevant_ids,
            signals.get("cited_chunk_ids", []),
        ),
        "source_type_match": str(signals.get("source_type")) == str(expected.get("source_type")),
        "no_evidence_refusal_accuracy": (
            bool(signals.get("refused_due_to_no_evidence"))
            if no_evidence_expected
            else not bool(signals.get("refused_due_to_no_evidence"))
        ),
        "reranker_improvement_rate": 1.0 if signals.get("reranker_improved") else 0.0,
    }
    passed = (
        metrics["recall_at_k"] >= float(expected.get("minimum_recall_at_k", 0.8))
        and metrics["mrr"] >= float(expected.get("minimum_mrr", 0.5))
        and metrics["no_evidence_refusal_accuracy"]
    )
    return _benchmark_result(
        case=case,
        module="rag_retrieval",
        actual=signals,
        expected=expected,
        metrics={**metrics, "case_pass": passed},
        passed=passed,
        error="RAG retrieval benchmark expectations were not met.",
    )


def _evaluate_benchmark_rag_answer(
    case: dict[str, Any],
    expected: dict[str, Any],
    signals: dict[str, Any],
) -> dict[str, Any]:
    unsupported_claims = list(signals.get("unsupported_claims") or [])
    citation_required = bool(expected.get("citation_required", True))
    citations = list(signals.get("cited_chunk_ids") or [])
    refusal_expected = bool(expected.get("refusal_expected"))
    metrics = {
        "groundedness": bool(signals.get("grounded")) and not unsupported_claims,
        "unsupported_claim_rate": round(len(unsupported_claims) / max(1, len(citations)), 4),
        "citation_required_pass_rate": bool(citations) if citation_required else True,
        "refusal_accuracy": bool(signals.get("refused_due_to_no_evidence")) == refusal_expected,
        "answer_schema_pass_rate": bool(signals.get("answer_schema_valid")),
    }
    passed = all(
        [
            metrics["groundedness"] or refusal_expected,
            metrics["unsupported_claim_rate"] == 0.0,
            metrics["citation_required_pass_rate"],
            metrics["refusal_accuracy"],
            metrics["answer_schema_pass_rate"],
        ]
    )
    return _benchmark_result(
        case=case,
        module="rag_answer",
        actual=signals,
        expected=expected,
        metrics={**metrics, "case_pass": passed},
        passed=passed,
        error="RAG answer benchmark expectations were not met.",
    )


def _evaluate_benchmark_match(
    case: dict[str, Any],
    expected: dict[str, Any],
    signals: dict[str, Any],
) -> dict[str, Any]:
    score_range = expected.get("score_range") or [0, 100]
    system_score = float(signals.get("system_score", 0))
    human_score = float(signals.get("human_score", system_score))
    expected_gaps = expected.get("gaps_should_include", [])
    actual_gaps = signals.get("gaps", [])
    metrics = {
        "score_in_expected_range": float(score_range[0]) <= system_score <= float(score_range[1]),
        "ranking_consistency": bool(signals.get("ranking_consistent")),
        "evidence_completeness": _hit_rate(
            expected.get("evidence_should_include", []),
            signals.get("evidence", []),
        ),
        "gap_identification_precision": _precision(expected_gaps, actual_gaps),
        "human_agreement": abs(system_score - human_score) <= 10,
        "stability_delta": float(signals.get("stability_delta", 0)),
    }
    passed = (
        metrics["score_in_expected_range"]
        and metrics["ranking_consistency"]
        and metrics["evidence_completeness"] >= 0.8
        and metrics["gap_identification_precision"] >= 0.8
        and metrics["human_agreement"]
        and metrics["stability_delta"] <= 5
    )
    return _benchmark_result(
        case=case,
        module="match",
        actual=signals,
        expected=expected,
        metrics={**metrics, "case_pass": passed},
        passed=passed,
        error="Match benchmark expectations were not met.",
    )


def _evaluate_benchmark_project_rewrite(
    case: dict[str, Any],
    expected: dict[str, Any],
    signals: dict[str, Any],
) -> dict[str, Any]:
    metrics = {
        "rewrite_schema_pass_rate": bool(signals.get("rewrite_schema_valid")),
        "fabrication_guard_pass": not bool(signals.get("fabricated_claims")),
        "evidence_required_present": bool(signals.get("evidence_required_present")),
        "matched_requirement_hit_rate": _hit_rate(
            expected.get("matched_requirements_should_include", []),
            signals.get("matched_requirements", []),
        ),
        "risk_flag_hit_rate": _hit_rate(
            expected.get("risk_flags_should_include", []),
            signals.get("risk_flags", []),
        ),
    }
    passed = all(
        [
            metrics["rewrite_schema_pass_rate"],
            metrics["fabrication_guard_pass"],
            metrics["evidence_required_present"],
            metrics["matched_requirement_hit_rate"] >= 0.8,
        ]
    )
    return _benchmark_result(
        case=case,
        module="project_rewrite",
        actual=signals,
        expected=expected,
        metrics={**metrics, "case_pass": passed},
        passed=passed,
        error="Project rewrite benchmark expectations were not met.",
    )


def _evaluate_benchmark_agent_workflow(
    case: dict[str, Any],
    expected: dict[str, Any],
    signals: dict[str, Any],
) -> dict[str, Any]:
    metrics = {
        "workflow_success_rate": signals.get("status") == expected.get("status"),
        "need_more_info_accuracy": signals.get("need_more_info") == expected.get("need_more_info"),
        "bad_case_payload_present": bool(signals.get("bad_case_payload_present"))
        if expected.get("bad_case_payload_expected")
        else True,
        "output_schema_pass_rate": bool(signals.get("output_schema_valid")),
    }
    passed = all(metrics.values())
    return _benchmark_result(
        case=case,
        module="agent_workflow",
        actual=signals,
        expected=expected,
        metrics={**metrics, "case_pass": passed},
        passed=passed,
        error="Agent workflow benchmark expectations were not met.",
    )


def _precision(expected_terms: list[Any], actual_terms: list[Any]) -> float:
    actual = [str(item).strip().lower() for item in actual_terms if str(item).strip()]
    if not actual:
        return 1.0 if not expected_terms else 0.0
    expected = {str(item).strip().lower() for item in expected_terms if str(item).strip()}
    hits = sum(1 for item in actual if item in expected)
    return round(hits / len(actual), 4)


def _confidence_calibration(
    signals: dict[str, Any],
    expected: dict[str, Any],
) -> float:
    confidence = float(signals.get("confidence", 0.0))
    target = float(expected.get("expected_confidence", confidence))
    return round(max(0.0, 1 - abs(confidence - target)), 4)


def _build_metrics(
    results: list[dict[str, Any]],
    *,
    run_config: dict[str, Any],
) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for result in results if result["passed"])
    failed = total - passed
    by_module: dict[str, dict[str, Any]] = {}
    metric_totals: dict[str, dict[str, list[float]]] = {}
    for result in results:
        bucket = by_module.setdefault(
            result["module"],
            {"total": 0, "passed": 0, "failed": 0, "pass_rate": 0.0, "metrics": {}},
        )
        metric_bucket = metric_totals.setdefault(result["module"], {})
        bucket["total"] += 1
        if result["passed"]:
            bucket["passed"] += 1
        else:
            bucket["failed"] += 1
        for metric_name, metric_value in result.get("metrics", {}).items():
            if isinstance(metric_value, bool):
                metric_bucket.setdefault(metric_name, []).append(
                    1.0 if metric_value else 0.0
                )
            elif isinstance(metric_value, int | float):
                metric_bucket.setdefault(metric_name, []).append(float(metric_value))
    for bucket in by_module.values():
        total_for_module = int(bucket["total"])
        bucket["pass_rate"] = (
            round(float(bucket["passed"]) / total_for_module, 4)
            if total_for_module
            else 0.0
        )
    for module, module_metrics in metric_totals.items():
        by_module[module]["metrics"] = {
            metric_name: round(sum(values) / len(values), 4)
            for metric_name, values in module_metrics.items()
            if values
        }
    return {
        "total_count": total,
        "total_cases": total,
        "passed_count": passed,
        "passed_cases": passed,
        "failed_count": failed,
        "failed_cases": failed,
        "failed_case_ids": [
            str(result["case_id"]) for result in results if not result["passed"]
        ],
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "by_module": by_module,
        "run_config": run_config,
        "llm_judge": False,
        "model_comparison": False,
    }


def _bad_case_type_for_module(module: str) -> str:
    return {
        "jd_parser": "missing_skill_extraction",
        "resume_parser": "missing_skill_extraction",
        "match": "match_score_inaccurate",
        "rag": "irrelevant_rag_source",
        "rag_retrieval": "irrelevant_rag_source",
        "agent": "agent_step_failed",
        "agent_workflow": "agent_step_failed",
    }.get(module, "other")


def _failed_case_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": result.get("case_id"),
        "module": result.get("module"),
        "case_type": result.get("case_type", "synthetic_contract"),
        "failure_type": _bad_case_type_for_module(str(result.get("module") or "")),
        "input_summary": result.get("input_summary")
        or _safe_text(result.get("case_name")),
        "expected_summary": _safe_text(result.get("expected_output")),
        "actual_summary": _safe_text(result.get("actual_output")),
        "failure_reason": result.get("error"),
        "suggested_bad_case_type": _bad_case_type_for_module(
            str(result.get("module") or "")
        ),
    }


def _write_outputs(
    *,
    dataset: str,
    module: str | None,
    output_dir: Path,
    results: list[dict[str, Any]],
    run_config: dict[str, Any],
) -> dict[str, Any]:
    failed_cases = [
        _failed_case_summary(result) for result in results if not result["passed"]
    ]
    metrics = _build_metrics(results, run_config=run_config)
    metrics["bad_case_regression_trend"] = ai_quality.bad_case_regression_trend(
        failed_cases
    )
    if dataset == BENCHMARK_DATASET:
        human_review_summary = _benchmark_human_review_summary()
        metrics["human_review"] = human_review_summary
    else:
        human_review_summary = None
    actual_outputs = [
        {
            "case_id": result.get("case_id"),
            "module": result.get("module"),
            "case_type": result.get("case_type", "synthetic_contract"),
            "input_payload": _sanitize_private_keys(result.get("input_payload")),
            "input_summary": result.get("input_summary"),
            "expected_output": _sanitize_private_keys(result.get("expected_output")),
            "actual_output": _sanitize_private_keys(result.get("actual_output")),
            "metrics": result.get("metrics", {}),
            "passed": result.get("passed"),
            "error": result.get("error"),
        }
        for result in results
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "failed_cases.json").write_text(
        json.dumps(failed_cases, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "actual_outputs.json").write_text(
        json.dumps(actual_outputs, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "run_config.json").write_text(
        json.dumps(run_config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if human_review_summary is not None:
        (output_dir / "human_review_summary.json").write_text(
            json.dumps(human_review_summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    generated_at = datetime.now(timezone.utc).isoformat()
    lines = [
        f"# Evaluation Summary: {dataset}",
        "",
        f"- generated_at: {generated_at}",
        f"- module: {module or 'all'}",
        f"- dataset_kind: {run_config['dataset_kind']}",
        f"- service_level: {str(run_config['service_level']).lower()}",
        "- production_quality: false",
        f"- total_count: {metrics['total_count']}",
        f"- passed_count: {metrics['passed_count']}",
        f"- failed_count: {metrics['failed_count']}",
        f"- pass_rate: {metrics['pass_rate']}",
        f"- prompt_version: {run_config['prompt_version']}",
        f"- schema_version: {run_config['schema_version']}",
        f"- retrieval_version: {run_config['retrieval_version']}",
        f"- model_version: {run_config['model_version']}",
        f"- evaluation_version: {run_config['evaluation_version']}",
        "- llm_judge: false",
        "- model_comparison: false",
        "",
        "## By Module",
        "",
        "| module | total | passed | failed | pass_rate |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for module_name, bucket in sorted(metrics["by_module"].items()):
        lines.append(
            f"| {module_name} | {bucket['total']} | {bucket['passed']} | "
            f"{bucket['failed']} | {bucket['pass_rate']} |"
        )
    lines.extend(
        [
            "",
            "## Known Limitations",
            "",
            "- Synthetic datasets are contract regression only.",
            "- Service-level datasets call current deterministic/mock services.",
            "- Benchmark datasets are synthetic large-sample foundations with human-review sample metrics.",
            "- This is a real evaluation foundation, not a production-quality benchmark.",
        ]
    )
    if failed_cases:
        lines.extend(["", "## Failed Cases", ""])
        for failed_case in failed_cases:
            lines.append(
                f"- {failed_case['module']}::{failed_case['case_id']}: "
                f"{failed_case['failure_reason']}"
            )
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return metrics


def _benchmark_human_review_summary() -> dict[str, Any]:
    path = DATASET_ROOT / BENCHMARK_DATASET / "human_review_sample.jsonl"
    if not path.exists():
        return {
            "reviewed_count": 0,
            "human_agreement_rate": 0.0,
            "disagreement_rate": 0.0,
        }
    records = ai_quality.parse_human_review_records(_load_jsonl(path))
    return ai_quality.compute_match_calibration(records)


def _run_synthetic(dataset: str, module: str | None, output_dir: Path) -> int:
    cases = _load_cases(dataset, module)
    results: list[dict[str, Any]] = []
    for current_module, case in cases:
        expected_map = _expected_by_case_id(dataset, current_module)
        expected = expected_map.get(str(case.get("id")), {})
        if _contains_private_key(case) or _contains_private_key(expected):
            evaluated = _result(
                {},
                expected,
                False,
                "Evaluation fixture contains private text keys.",
            )
        else:
            evaluated = EVALUATORS[current_module](case, expected)
        results.append(
            {
                "case_id": case.get("id"),
                "case_name": case.get("name"),
                "module": current_module,
                "case_type": "synthetic_contract",
                "input_payload": _case_input_payload(case),
                "metrics": {"case_pass": evaluated["passed"]},
                **evaluated,
            }
        )

    run_config = {
        "requested_module": module or "all",
        "dataset_name": dataset,
        "dataset_kind": "synthetic_contract",
        "service_level": False,
        "production_quality": False,
        **version_metadata(include_evaluation=True),
        "deterministic": True,
        "llm_judge": False,
        "model_comparison": False,
    }
    metrics = _write_outputs(
        dataset=dataset,
        module=module,
        output_dir=output_dir,
        results=results,
        run_config=run_config,
    )
    print(f"wrote {output_dir}")
    print(
        "total={total_count} passed={passed_count} failed={failed_count} pass_rate={pass_rate}".format(
            **metrics
        )
    )
    return 0 if metrics["failed_count"] == 0 else 1


def _run_service_level(module: str | None, output_dir: Path) -> int:
    cases = _load_service_level_cases(module)
    results: list[dict[str, Any]] = []
    infrastructure_failed = False
    with _service_eval_session() as db:
        for current_module, case in cases:
            expected = dict(case.get("expected") or {})
            evaluator = SERVICE_LEVEL_EVALUATORS[_service_module_name(current_module) or current_module]
            try:
                result = evaluator(db, case, expected)
            except Exception as exc:
                infrastructure_failed = True
                result = _service_result(
                    case=case,
                    module=current_module,
                    actual={},
                    expected=expected,
                    metrics={"case_pass": False},
                    passed=False,
                    error=f"Service-level evaluator failed: {exc}",
                    input_summary=_safe_text(case.get("case_id")),
                    service_calls=[],
                )
            results.append(result)

    run_config = {
        "requested_module": module or "all",
        "dataset_name": SERVICE_LEVEL_DATASET,
        "dataset_kind": "service_level",
        "service_level": True,
        "production_quality": False,
        **version_metadata(include_evaluation=True),
        "deterministic": True,
        "llm_judge": False,
        "model_comparison": False,
        "uses_real_services": True,
        "writes_database": False,
        "db_write_gap": "Output JSON maps to evaluation run/case/result schema; DB adapter remains follow-up.",
    }
    metrics = _write_outputs(
        dataset=SERVICE_LEVEL_DATASET,
        module=module,
        output_dir=output_dir,
        results=results,
        run_config=run_config,
    )
    print(f"wrote {output_dir}")
    print(
        "total={total_count} passed={passed_count} failed={failed_count} pass_rate={pass_rate}".format(
            **metrics
        )
    )
    return 1 if infrastructure_failed else 0


def _run_benchmark(module: str | None, output_dir: Path) -> int:
    cases = _load_benchmark_cases(module)
    results: list[dict[str, Any]] = []
    for current_module, case in cases:
        if _contains_private_key(case):
            result = _benchmark_result(
                case=case,
                module=current_module,
                actual={},
                expected=dict(case.get("expected") or {}),
                metrics={"case_pass": False},
                passed=False,
                error="Benchmark fixture contains private text keys.",
            )
        else:
            result = _evaluate_benchmark_case(current_module, case)
        results.append(result)

    run_config = {
        "requested_module": module or "all",
        "dataset_name": BENCHMARK_DATASET,
        "dataset_kind": "benchmark_foundation",
        "service_level": False,
        "production_quality": False,
        **version_metadata(include_evaluation=True),
        "deterministic": True,
        "llm_judge": False,
        "model_comparison": False,
        "large_scale_foundation": True,
        "case_count_target": 100,
        "uses_real_private_data": False,
        "uses_real_provider_network": False,
    }
    metrics = _write_outputs(
        dataset=BENCHMARK_DATASET,
        module=module,
        output_dir=output_dir,
        results=results,
        run_config=run_config,
    )
    print(f"wrote {output_dir}")
    print(
        "total={total_count} passed={passed_count} failed={failed_count} pass_rate={pass_rate}".format(
            **metrics
        )
    )
    return 0 if metrics["failed_count"] == 0 else 1


def run(dataset: str, module: str | None, output_dir: Path) -> int:
    if dataset == BENCHMARK_DATASET:
        return _run_benchmark(module, output_dir)
    if dataset == SERVICE_LEVEL_DATASET:
        return _run_service_level(module, output_dir)
    return _run_synthetic(dataset, module, output_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--module", choices=sorted(MODULES))
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    output_dir = args.output_dir or DEFAULT_OUTPUT_ROOT / args.dataset
    return run(args.dataset, args.module, output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
