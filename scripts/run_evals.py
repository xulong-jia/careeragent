#!/usr/bin/env python3
"""Run deterministic privacy-safe evaluation fixtures."""

from __future__ import annotations

import argparse
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
MODULES = {
    "jd_parser",
    "resume_parser",
    "match",
    "rag",
    "agent",
    "application",
    "bad_case",
}
PRIVATE_TEXT_KEYS = {
    "raw_text",
    "jd_raw_text",
    "chunk_text",
    "full_text",
    "resume_text",
    "job_text",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _expected_by_case_id(dataset: str, module: str) -> dict[str, dict[str, Any]]:
    expected_path = EXPECTED_ROOT / dataset / f"{module}_expected.json"
    if not expected_path.exists():
        return {}
    payload = _load_json(expected_path)
    return {
        str(item["id"]): item.get("expected", {})
        for item in payload.get("cases", [])
        if "id" in item
    }


def _load_cases(dataset: str, module: str | None) -> list[tuple[str, dict[str, Any]]]:
    dataset_dir = DATASET_ROOT / dataset
    if not dataset_dir.exists():
        return []
    modules = [module] if module else sorted(MODULES)
    cases: list[tuple[str, dict[str, Any]]] = []
    for current_module in modules:
        if current_module not in MODULES:
            raise ValueError(f"Unsupported module: {current_module}")
        path = dataset_dir / f"{current_module}_smoke.json"
        if not path.exists():
            continue
        payload = _load_json(path)
        for case in payload.get("cases", []):
            cases.append((current_module, case))
    return cases


def _build_metrics(
    results: list[dict[str, Any]],
    *,
    run_config: dict[str, Any],
) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for result in results if result["passed"])
    failed = total - passed
    by_module: dict[str, dict[str, int | float]] = {}
    for result in results:
        bucket = by_module.setdefault(
            result["module"],
            {"total": 0, "passed": 0, "failed": 0, "pass_rate": 0.0},
        )
        bucket["total"] += 1
        if result["passed"]:
            bucket["passed"] += 1
        else:
            bucket["failed"] += 1
    for bucket in by_module.values():
        total_for_module = int(bucket["total"])
        bucket["pass_rate"] = (
            round(float(bucket["passed"]) / total_for_module, 4)
            if total_for_module
            else 0.0
        )
    return {
        "total_count": total,
        "passed_count": passed,
        "failed_count": failed,
        "failed_case_ids": [
            str(result["case_id"]) for result in results if not result["passed"]
        ],
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "by_module": by_module,
        "run_config": run_config,
        "llm_judge": False,
        "model_comparison": False,
    }


def run(dataset: str, module: str | None, output_dir: Path) -> int:
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
                **evaluated,
            }
        )

    run_config = {
        "requested_module": module or "all",
        "dataset_name": dataset,
        **version_metadata(include_evaluation=True),
        "deterministic": True,
        "llm_judge": False,
        "model_comparison": False,
    }
    metrics = _build_metrics(results, run_config=run_config)
    failed_cases = [result for result in results if not result["passed"]]
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "failed_cases.json").write_text(
        json.dumps(failed_cases, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    generated_at = datetime.now(timezone.utc).isoformat()
    summary = [
        f"# Evaluation Summary: {dataset}",
        "",
        f"- generated_at: {generated_at}",
        f"- module: {module or 'all'}",
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
    ]
    (output_dir / "summary.md").write_text("\n".join(summary), encoding="utf-8")
    print(f"wrote {output_dir}")
    print(
        "total={total_count} passed={passed_count} failed={failed_count} pass_rate={pass_rate}".format(
            **metrics
        )
    )
    return 0 if metrics["failed_count"] == 0 else 1


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
