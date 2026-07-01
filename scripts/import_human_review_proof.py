#!/usr/bin/env python3
"""Import redacted human review evidence into the v3.5 proof shape."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
import uuid


REQUIRED_FIELDS = {
    "reviewer_id",
    "rubric_version",
    "module",
    "case_id",
    "human_score",
    "human_label",
    "confidence",
    "accepted_output",
    "rejected_output",
    "correction_note",
    "privacy_review_passed",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact_reviewer(reviewer_id: str) -> str:
    digest = hashlib.sha256(reviewer_id.encode("utf-8")).hexdigest()[:12]
    return f"reviewer:{digest}"


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "pass", "passed"}


def _parse_score(value: Any) -> float:
    return float(str(value).strip())


def load_review_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        rows = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    else:
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

    missing_by_row: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        missing = sorted(field for field in REQUIRED_FIELDS if field not in row)
        if missing:
            missing_by_row.append({"row": index, "missing": missing})
    if missing_by_row:
        raise ValueError(f"review input missing required fields: {missing_by_row}")
    return rows


def _agreement_rate(records: list[dict[str, Any]]) -> tuple[float, int]:
    by_case: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_case.setdefault(str(record["case_id"]), []).append(record)

    comparable = 0
    agreed = 0
    for case_records in by_case.values():
        if len(case_records) < 2:
            continue
        comparable += 1
        labels = {str(item["human_label"]).strip().lower() for item in case_records}
        accepted = {_parse_bool(item["accepted_output"]) for item in case_records}
        scores = [_parse_score(item["human_score"]) for item in case_records]
        if len(labels) == 1 and len(accepted) == 1 and max(scores) - min(scores) <= 10:
            agreed += 1
    if comparable == 0:
        return 0.0, 0
    return agreed / comparable, comparable


def build_human_review_proof(
    input_path: Path,
    *,
    batch_id: str | None = None,
) -> dict[str, Any]:
    records = load_review_records(input_path)
    reviewer_ids = sorted({str(record["reviewer_id"]).strip() for record in records})
    redacted_reviewers = [_redact_reviewer(reviewer_id) for reviewer_id in reviewer_ids]
    modules = sorted({str(record["module"]).strip() for record in records})
    rubrics = sorted({str(record["rubric_version"]).strip() for record in records})
    case_ids = {str(record["case_id"]).strip() for record in records}
    agreement_rate, comparable_cases = _agreement_rate(records)
    adjudication_required = 0
    for record in records:
        status = str(record.get("adjudication_status", "")).strip().lower()
        if status in {"required", "pending", "needs_adjudication"}:
            adjudication_required += 1
    privacy_passed = all(_parse_bool(record["privacy_review_passed"]) for record in records)

    limitations: list[str] = []
    if comparable_cases == 0:
        limitations.append("No multi-reviewer comparable cases were present.")
    if len(rubrics) != 1:
        limitations.append("Multiple rubric versions are present in this batch.")
    if not privacy_passed:
        limitations.append("At least one row failed privacy review.")

    return {
        "proof_type": "human_review",
        "review_batch_id": batch_id or f"human-review-{uuid.uuid4().hex[:12]}",
        "generated_at": _utc_now(),
        "reviewer_count": len(reviewer_ids),
        "reviewer_ids_redacted": redacted_reviewers,
        "rubric_version": rubrics[0] if rubrics else "",
        "case_count": len(case_ids),
        "modules_covered": modules,
        "agreement_rate": round(agreement_rate, 4),
        "adjudication_required_count": adjudication_required,
        "privacy_review_passed": privacy_passed,
        "limitations": limitations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--batch-id")
    args = parser.parse_args()

    proof = build_human_review_proof(args.input, batch_id=args.batch_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(str(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
