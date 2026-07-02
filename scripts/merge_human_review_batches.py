#!/usr/bin/env python3
"""Merge independent human review batch proofs into one multi-reviewer proof."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
import uuid

try:
    from .import_human_review_batch import (
        _agreement_metrics,
        summarize_items,
        validate_human_review_batch_payload,
    )
except ImportError:  # pragma: no cover - direct script execution path
    from import_human_review_batch import (  # type: ignore
        _agreement_metrics,
        summarize_items,
        validate_human_review_batch_payload,
    )


DEFAULT_OUTPUT = "evidence/private_outputs/human_review_merged.{timestamp}.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _output_path(path: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path(path.format(timestamp=timestamp))


def _load_batch(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("proof_type") != "human_review":
        raise ValueError(f"{path}: proof_type must be human_review")
    errors = validate_human_review_batch_payload(payload)
    if errors:
        raise ValueError(f"{path}: invalid human review batch: {errors}")
    return payload


def _first_non_empty(batches: list[dict[str, Any]], field: str, default: str = "") -> str:
    for batch in batches:
        value = str(batch.get(field, "")).strip()
        if value:
            return value
    return default


def merge_human_review_batches(
    input_paths: list[Path],
    *,
    batch_id: str | None = None,
    dataset_name: str | None = None,
    sampling_method: str | None = None,
    reviewer_role: str | None = None,
) -> dict[str, Any]:
    if len(input_paths) < 2:
        raise ValueError("at least two human review batch inputs are required")

    batches = [_load_batch(path) for path in input_paths]
    items: list[dict[str, Any]] = []
    seen_reviewer_item: set[tuple[str, str]] = set()
    for batch in batches:
        for item in batch.get("review_items", []):
            key = (str(item.get("reviewer_id_hash", "")), str(item.get("item_id", "")))
            if key in seen_reviewer_item:
                raise ValueError(
                    "duplicate review for same reviewer_id_hash and item_id: "
                    f"{key[0]} / {key[1]}"
                )
            seen_reviewer_item.add(key)
            items.append(dict(item))

    reviewer_hashes = sorted({str(item["reviewer_id_hash"]).strip() for item in items})
    reviewer_roles = sorted(
        {
            role
            for role in [
                reviewer_role,
                *(role for batch in batches for role in batch.get("reviewer_roles", [])),
            ]
            if str(role or "").strip()
        }
    )
    unique_item_ids = sorted({str(item["item_id"]) for item in items})
    summary = summarize_items(items)
    agreement = _agreement_metrics(items)
    privacy_sanitized = all(batch.get("privacy_sanitized") is True for batch in batches)

    limitations: list[str] = []
    if len(reviewer_hashes) < 2:
        limitations.append("At least two independent reviewers are required.")
    if agreement["comparable_item_count"] < len(unique_item_ids):
        limitations.append("Not every review item has multiple reviewer judgments.")
    if not privacy_sanitized:
        limitations.append("At least one input batch was not marked privacy_sanitized.")
    limitations.extend(summary["threshold_failures"])

    return {
        "proof_type": "human_review",
        "review_batch_id": batch_id or f"human-review-merged-{uuid.uuid4().hex[:12]}",
        "created_at": _utc_now(),
        "reviewer_count": len(reviewer_hashes),
        "reviewer_roles": reviewer_roles,
        "dataset_name": dataset_name or _first_non_empty(batches, "dataset_name", "merged_human_review"),
        "sample_size": len(unique_item_ids),
        "sampling_method": sampling_method
        or "merged_multi_reviewer_batches:"
        + ",".join(str(path.name) for path in input_paths),
        "privacy_sanitized": privacy_sanitized,
        "review_items": items,
        "agreement_metrics": agreement,
        "adjudication_required_count": summary["adjudication_required_count"],
        "adjudication_completed_count": summary["adjudication_completed_count"],
        "bad_case_count": summary["bad_case_count"],
        "summary": summary,
        "production_quality_candidate_signal": (
            summary["production_quality_candidate_signal"]
            and len(reviewer_hashes) >= 2
            and privacy_sanitized
            and agreement["comparable_item_count"] >= len(unique_item_ids)
        ),
        "limitations": limitations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, action="append")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-id")
    parser.add_argument("--dataset-name")
    parser.add_argument("--sampling-method")
    parser.add_argument("--reviewer-role")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    payload = merge_human_review_batches(
        args.input,
        batch_id=args.batch_id,
        dataset_name=args.dataset_name,
        sampling_method=args.sampling_method,
        reviewer_role=args.reviewer_role,
    )
    errors = validate_human_review_batch_payload(payload)
    if errors:
        raise ValueError(f"invalid merged human review batch: {errors}")

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
