#!/usr/bin/env python3
"""Import external human review batch evidence without storing private rows."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any
import uuid


DEFAULT_OUTPUT = "evidence/private_outputs/human_review_batch.{timestamp}.json"
TASK_TYPES = {
    "jd_parse",
    "resume_parse",
    "match_score",
    "rag_answer",
    "project_rewrite",
    "agent_workflow",
}
DECISIONS = {"pass", "minor_issue", "major_issue", "fail"}
REQUIRED_ITEM_FIELDS = {
    "item_id",
    "task_type",
    "anonymized_input_ref",
    "model_output_ref",
    "reviewer_id_hash",
    "correctness_score",
    "groundedness_score",
    "safety_score",
    "usefulness_score",
    "privacy_risk_flag",
    "hallucination_flag",
    "fabrication_flag",
    "reviewer_comment",
    "decision",
    "requires_adjudication",
    "adjudication_decision",
    "bad_case_ref",
}
BATCH_OPTIONAL_FIELDS = {
    "review_batch_id",
    "dataset_name",
    "sampling_method",
    "reviewer_role",
    "privacy_sanitized",
}
PII_PATTERNS = [
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{8,}\d)(?!\d)"),
]
RAW_PRIVATE_FIELDS = {
    "raw_text",
    "raw_resume",
    "resume_text",
    "jd_text",
    "chunk_text",
    "interview_answer",
    "private_note",
    "provider_trace",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _output_path(path: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path(path.format(timestamp=timestamp))


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "pass", "passed"}


def _parse_score(value: Any, *, field: str, row_number: int) -> float:
    try:
        score = float(str(value).strip())
    except ValueError as exc:
        raise ValueError(f"row {row_number}: {field} must be a number") from exc
    if not 0 <= score <= 1:
        raise ValueError(f"row {row_number}: {field} must be between 0 and 1")
    return score


def _reviewer_hash(value: str) -> str:
    raw = value.strip()
    if not raw:
        raise ValueError("reviewer_id_hash is required")
    if raw.startswith("reviewer:") or raw.startswith("reviewer_"):
        return raw
    return "reviewer:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _check_no_private_data(row: dict[str, Any], *, row_number: int) -> None:
    for key, value in row.items():
        text = "" if value is None else str(value)
        if key in RAW_PRIVATE_FIELDS and text.strip():
            raise ValueError(f"row {row_number}: private field {key} is not allowed")
        for pattern in PII_PATTERNS:
            if pattern.search(text):
                raise ValueError(f"row {row_number}: obvious PII detected in {key}")


def load_review_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        rows = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    else:
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("human review input is empty")
    return rows


def normalize_review_items(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row_number, row in enumerate(rows, start=1):
        _check_no_private_data(row, row_number=row_number)
        missing = sorted(field for field in REQUIRED_ITEM_FIELDS if field not in row)
        if missing:
            raise ValueError(f"row {row_number}: missing required fields: {missing}")

        task_type = str(row["task_type"]).strip()
        if task_type not in TASK_TYPES:
            raise ValueError(f"row {row_number}: unsupported task_type {task_type!r}")
        decision = str(row["decision"]).strip()
        if decision not in DECISIONS:
            raise ValueError(f"row {row_number}: unsupported decision {decision!r}")

        item = {
            "item_id": str(row["item_id"]).strip(),
            "task_type": task_type,
            "anonymized_input_ref": str(row["anonymized_input_ref"]).strip(),
            "model_output_ref": str(row["model_output_ref"]).strip(),
            "reviewer_id_hash": _reviewer_hash(str(row["reviewer_id_hash"])),
            "correctness_score": _parse_score(
                row["correctness_score"],
                field="correctness_score",
                row_number=row_number,
            ),
            "groundedness_score": _parse_score(
                row["groundedness_score"],
                field="groundedness_score",
                row_number=row_number,
            ),
            "safety_score": _parse_score(row["safety_score"], field="safety_score", row_number=row_number),
            "usefulness_score": _parse_score(
                row["usefulness_score"],
                field="usefulness_score",
                row_number=row_number,
            ),
            "privacy_risk_flag": _parse_bool(row["privacy_risk_flag"]),
            "hallucination_flag": _parse_bool(row["hallucination_flag"]),
            "fabrication_flag": _parse_bool(row["fabrication_flag"]),
            "reviewer_comment": str(row["reviewer_comment"]).strip(),
            "decision": decision,
            "requires_adjudication": _parse_bool(row["requires_adjudication"]),
            "adjudication_decision": str(row["adjudication_decision"]).strip(),
            "bad_case_ref": str(row["bad_case_ref"]).strip(),
        }
        if not item["item_id"]:
            raise ValueError(f"row {row_number}: item_id is required")
        if not item["anonymized_input_ref"] or not item["model_output_ref"]:
            raise ValueError(f"row {row_number}: review refs must be non-empty")
        items.append(item)
    return items


def summarize_items(
    items: list[dict[str, Any]],
    *,
    min_sample_size: int = 30,
    min_pass_rate: float = 0.90,
    max_hallucination_rate: float = 0.02,
    max_fabrication_rate: float = 0.01,
    max_privacy_risk_count: int = 0,
    min_adjudication_completion_rate: float = 1.0,
) -> dict[str, Any]:
    total = len(items)
    decisions = [item["decision"] for item in items]
    pass_count = decisions.count("pass")
    minor_count = decisions.count("minor_issue")
    major_count = decisions.count("major_issue")
    fail_count = decisions.count("fail")
    hallucination_count = sum(1 for item in items if item["hallucination_flag"])
    fabrication_count = sum(1 for item in items if item["fabrication_flag"])
    privacy_risk_count = sum(1 for item in items if item["privacy_risk_flag"])
    adjudication_required = [item for item in items if item["requires_adjudication"]]
    adjudication_completed = [
        item for item in adjudication_required if item["adjudication_decision"].strip()
    ]
    bad_case_count = sum(1 for item in items if item["bad_case_ref"].strip())

    def avg(field: str) -> float:
        if not total:
            return 0.0
        return round(sum(float(item[field]) for item in items) / total, 4)

    adjudication_completion_rate = (
        1.0 if not adjudication_required else len(adjudication_completed) / len(adjudication_required)
    )
    pass_rate = pass_count / total if total else 0.0
    hallucination_rate = hallucination_count / total if total else 0.0
    fabrication_rate = fabrication_count / total if total else 0.0
    threshold_failures: list[str] = []
    if total < min_sample_size:
        threshold_failures.append("insufficient_sample_size")
    if pass_rate < min_pass_rate:
        threshold_failures.append("pass_rate_below_threshold")
    if hallucination_rate > max_hallucination_rate:
        threshold_failures.append("hallucination_rate_above_threshold")
    if fabrication_rate > max_fabrication_rate:
        threshold_failures.append("fabrication_rate_above_threshold")
    if privacy_risk_count > max_privacy_risk_count:
        threshold_failures.append("privacy_risk_count_above_threshold")
    if adjudication_completion_rate < min_adjudication_completion_rate:
        threshold_failures.append("adjudication_incomplete")

    return {
        "total_items": total,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "minor_issue_count": minor_count,
        "major_issue_count": major_count,
        "pass_rate": round(pass_rate, 4),
        "average_correctness_score": avg("correctness_score"),
        "average_groundedness_score": avg("groundedness_score"),
        "average_safety_score": avg("safety_score"),
        "hallucination_rate": round(hallucination_rate, 4),
        "fabrication_rate": round(fabrication_rate, 4),
        "privacy_risk_count": privacy_risk_count,
        "adjudication_completion_rate": round(adjudication_completion_rate, 4),
        "adjudication_required_count": len(adjudication_required),
        "adjudication_completed_count": len(adjudication_completed),
        "bad_case_count": bad_case_count,
        "threshold_failures": threshold_failures,
        "production_quality_candidate_signal": not threshold_failures,
    }


def _agreement_metrics(items: list[dict[str, Any]]) -> dict[str, Any]:
    by_item: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        by_item.setdefault(item["item_id"], []).append(item)
    comparable = 0
    agreed = 0
    for group in by_item.values():
        if len(group) < 2:
            continue
        comparable += 1
        decisions = {item["decision"] for item in group}
        if len(decisions) == 1:
            agreed += 1
    return {
        "comparable_item_count": comparable,
        "decision_agreement_rate": round(agreed / comparable, 4) if comparable else 0.0,
    }


def _batch_value(rows: list[dict[str, Any]], key: str, default: str = "") -> str:
    for row in rows:
        value = str(row.get(key, "")).strip()
        if value:
            return value
    return default


def build_human_review_batch(
    input_path: Path,
    *,
    batch_id: str | None = None,
    dataset_name: str | None = None,
    sampling_method: str | None = None,
    reviewer_role: str | None = None,
    privacy_sanitized: bool | None = None,
) -> dict[str, Any]:
    rows = load_review_rows(input_path)
    for row_number, row in enumerate(rows, start=1):
        _check_no_private_data(
            {key: row.get(key, "") for key in BATCH_OPTIONAL_FIELDS},
            row_number=row_number,
        )
    items = normalize_review_items(rows)
    summary = summarize_items(items)
    reviewer_hashes = sorted({item["reviewer_id_hash"] for item in items})
    row_roles = sorted(
        {str(row.get("reviewer_role", "")).strip() for row in rows if str(row.get("reviewer_role", "")).strip()}
    )
    roles = sorted({role for role in [reviewer_role, *row_roles] if role})
    sanitized = privacy_sanitized
    if sanitized is None:
        sanitized = all(_parse_bool(row.get("privacy_sanitized", "false")) for row in rows)

    limitations: list[str] = []
    if len(reviewer_hashes) < 2:
        limitations.append("At least two independent reviewers are required.")
    if not sanitized:
        limitations.append("Input dataset was not marked privacy_sanitized.")
    limitations.extend(summary["threshold_failures"])

    return {
        "proof_type": "human_review",
        "review_batch_id": batch_id
        or _batch_value(rows, "review_batch_id")
        or f"human-review-{uuid.uuid4().hex[:12]}",
        "created_at": _utc_now(),
        "reviewer_count": len(reviewer_hashes),
        "reviewer_roles": roles,
        "dataset_name": dataset_name or _batch_value(rows, "dataset_name", "anonymized_review_batch"),
        "sample_size": summary["total_items"],
        "sampling_method": sampling_method or _batch_value(rows, "sampling_method", "documented_external_sample"),
        "privacy_sanitized": bool(sanitized),
        "review_items": items,
        "agreement_metrics": _agreement_metrics(items),
        "adjudication_required_count": summary["adjudication_required_count"],
        "adjudication_completed_count": summary["adjudication_completed_count"],
        "bad_case_count": summary["bad_case_count"],
        "summary": summary,
        "production_quality_candidate_signal": (
            summary["production_quality_candidate_signal"]
            and len(reviewer_hashes) >= 2
            and bool(sanitized)
        ),
        "limitations": limitations,
    }


def validate_human_review_batch_payload(payload: dict[str, Any]) -> list[str]:
    required = {
        "review_batch_id",
        "created_at",
        "reviewer_count",
        "reviewer_roles",
        "dataset_name",
        "sample_size",
        "sampling_method",
        "privacy_sanitized",
        "review_items",
        "agreement_metrics",
        "adjudication_required_count",
        "adjudication_completed_count",
        "bad_case_count",
        "production_quality_candidate_signal",
        "limitations",
    }
    errors = [f"missing required field: {field}" for field in sorted(required) if field not in payload]
    if payload.get("proof_type") != "human_review":
        errors.append("proof_type must be human_review")
    for index, item in enumerate(payload.get("review_items", []), start=1):
        missing = sorted(field for field in REQUIRED_ITEM_FIELDS if field not in item)
        errors.extend(f"review_items[{index}] missing required field: {field}" for field in missing)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-id")
    parser.add_argument("--dataset-name")
    parser.add_argument("--sampling-method")
    parser.add_argument("--reviewer-role")
    parser.add_argument("--privacy-sanitized", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    payload = build_human_review_batch(
        args.input,
        batch_id=args.batch_id,
        dataset_name=args.dataset_name,
        sampling_method=args.sampling_method,
        reviewer_role=args.reviewer_role,
        privacy_sanitized=args.privacy_sanitized if args.privacy_sanitized else None,
    )
    errors = validate_human_review_batch_payload(payload)
    if errors:
        raise ValueError(f"invalid human review batch: {errors}")

    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.dry_run:
        print(rendered, end="")
        return 0
    output = _output_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
