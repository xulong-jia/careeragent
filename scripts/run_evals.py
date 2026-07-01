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
    "rag_retrieval": "rag_retrieval_cases.json",
    "agent_workflow": "agent_workflow_cases.json",
}
SERVICE_LEVEL_MODULE_ALIASES = {
    "rag": "rag_retrieval",
    "agent": "agent_workflow",
}
MODULES = SYNTHETIC_MODULES | set(SERVICE_LEVEL_MODULE_FILES)
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
        "role_category": profile.role_category,
        "required_skills": profile.required_skills,
        "preferred_skills": profile.preferred_skills,
        "responsibilities": profile.responsibilities,
        "summary": profile.summary,
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
    }
    passed = (
        role_match
        and required_hits >= int(expected.get("minimum_required_skill_hits", 0))
        and preferred_hits >= int(expected.get("minimum_preferred_skill_hits", 0))
        and responsibility_hits >= int(expected.get("minimum_responsibility_hits", 0))
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
        "risk_flags_match": sorted(risk_types)
        == sorted(str(item) for item in expected.get("risk_flags_expected", [])),
    }
    passed = all(
        [
            metrics["section_hit_rate"] == 1.0,
            metrics["skill_hit_rate"] == 1.0,
            metrics["project_hit_rate"] == 1.0,
            metrics["education_hit_rate"] == 1.0,
            metrics["risk_flags_match"],
        ]
    )
    actual = {
        "resume_id": resume.resume_id,
        "sections": sections,
        "skills": skill_values,
        "projects": structured.get("projects", []),
        "education": structured.get("education", []),
        "risk_flags": risk_types,
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
    from app.schemas.matches import MatchRunRequest
    from app.services import match_service

    case_input = dict(case.get("input") or {})
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
    evidence_dimensions = [item.dimension for item in report.evidence]
    score_range = expected.get("score_range") or [0, 100]
    metrics = {
        "evidence_dimension_coverage": _hit_rate(
            expected.get("required_evidence_dimensions", []),
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
        "risk_flags_match": sorted(report.risk_flags)
        == sorted(expected.get("risk_flags_expected", [])),
    }
    passed = all(
        [
            metrics["evidence_dimension_coverage"] == 1.0,
            metrics["strength_keyword_hit_rate"] == 1.0,
            metrics["gap_keyword_hit_rate"] == 1.0,
            metrics["score_in_expected_range"],
            metrics["risk_flags_match"],
        ]
    )
    actual = {
        "match_report_id": report.match_report_id,
        "total_score": report.total_score,
        "dimension_scores": report.dimension_scores,
        "evidence": [item.model_dump() for item in report.evidence],
        "strengths": report.strengths,
        "gaps": report.gaps,
        "risk_flags": report.risk_flags,
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
    from app.agents.runner import run_workflow
    from app.agents.workflows import get_workflow_definition
    from app.repositories import agent_repository

    case_input = dict(case.get("input") or {})
    seed = dict(case_input.get("seed_data") or {})
    payload = dict(case_input.get("payload") or {})
    if seed:
        resume_seed = dict(seed.get("resume") or {})
        jd_seed = dict(seed.get("jd") or {})
        resume = _create_resume_from_text(
            db,
            str(resume_seed.get("filename") or "agent_resume.txt"),
            str(resume_seed.get("raw_text") or ""),
        )
        job = _create_job_from_input(db, jd_seed)
        payload.setdefault("resume_version_id", resume.resume_id + "_version_0001")
        payload.setdefault("jd_id", job.jd_id)

    workflow_name = str(
        payload.get("workflow_name")
        or case_input.get("workflow_name")
        or "job_application_preparation"
    )
    workflow = get_workflow_definition(workflow_name)
    if workflow is None:
        raise ValueError(f"Unsupported workflow: {workflow_name}")
    run = run_workflow(db, workflow=workflow, payload=payload)
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
    metrics = {
        "expected_status_match": run.status == expected.get("expected_status"),
        "expected_step_coverage": step_coverage,
        "expected_missing_slot_match": missing_slot_match,
    }
    passed = all(
        [
            metrics["expected_status_match"],
            step_coverage == 1.0,
            missing_slot_match,
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
                "status": step.status,
            }
            for step in steps
        ],
        "missing_slots": run.missing_slots or [],
        "questions": run.questions or [],
        "output_refs": run.output_refs,
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
        service_calls=["agent.runner.run_workflow"],
    )


SERVICE_LEVEL_EVALUATORS = {
    "jd_parser": _evaluate_service_jd_parser,
    "resume_parser": _evaluate_service_resume_parser,
    "match": _evaluate_service_match,
    "rag_retrieval": _evaluate_service_rag_retrieval,
    "agent_workflow": _evaluate_service_agent_workflow,
}


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
    metrics = _build_metrics(results, run_config=run_config)
    failed_cases = [
        _failed_case_summary(result) for result in results if not result["passed"]
    ]
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


def run(dataset: str, module: str | None, output_dir: Path) -> int:
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
