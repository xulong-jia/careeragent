#!/usr/bin/env python3
"""Summarize human review evidence and evaluate configurable thresholds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .import_human_review_batch import (
        build_human_review_batch,
        load_review_rows,
        normalize_review_items,
        summarize_items,
    )
except ImportError:  # pragma: no cover - direct script execution path
    from import_human_review_batch import (  # type: ignore
        build_human_review_batch,
        load_review_rows,
        normalize_review_items,
        summarize_items,
    )


def _items_from_input(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "review_items" in payload:
            return list(payload["review_items"])
    return normalize_review_items(load_review_rows(path))


def build_human_review_summary(
    input_path: Path,
    *,
    min_sample_size: int = 30,
    min_pass_rate: float = 0.90,
    max_hallucination_rate: float = 0.02,
    max_fabrication_rate: float = 0.01,
    max_privacy_risk_count: int = 0,
    min_adjudication_completion_rate: float = 1.0,
) -> dict[str, Any]:
    if input_path.suffix.lower() == ".json":
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        source_batch_id = payload.get("review_batch_id", input_path.stem)
        dataset_name = payload.get("dataset_name", "")
    else:
        payload = build_human_review_batch(input_path)
        source_batch_id = payload["review_batch_id"]
        dataset_name = payload["dataset_name"]

    items = _items_from_input(input_path)
    summary = summarize_items(
        items,
        min_sample_size=min_sample_size,
        min_pass_rate=min_pass_rate,
        max_hallucination_rate=max_hallucination_rate,
        max_fabrication_rate=max_fabrication_rate,
        max_privacy_risk_count=max_privacy_risk_count,
        min_adjudication_completion_rate=min_adjudication_completion_rate,
    )
    return {
        "summary_type": "human_review_summary",
        "source_review_batch_id": source_batch_id,
        "dataset_name": dataset_name,
        **summary,
        "thresholds": {
            "min_sample_size": min_sample_size,
            "min_pass_rate": min_pass_rate,
            "max_hallucination_rate": max_hallucination_rate,
            "max_fabrication_rate": max_fabrication_rate,
            "max_privacy_risk_count": max_privacy_risk_count,
            "min_adjudication_completion_rate": min_adjudication_completion_rate,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--min-sample-size", type=int, default=30)
    parser.add_argument("--min-pass-rate", type=float, default=0.90)
    parser.add_argument("--max-hallucination-rate", type=float, default=0.02)
    parser.add_argument("--max-fabrication-rate", type=float, default=0.01)
    parser.add_argument("--max-privacy-risk-count", type=int, default=0)
    parser.add_argument("--min-adjudication-completion-rate", type=float, default=1.0)
    args = parser.parse_args()

    summary = build_human_review_summary(
        args.input,
        min_sample_size=args.min_sample_size,
        min_pass_rate=args.min_pass_rate,
        max_hallucination_rate=args.max_hallucination_rate,
        max_fabrication_rate=args.max_fabrication_rate,
        max_privacy_risk_count=args.max_privacy_risk_count,
        min_adjudication_completion_rate=args.min_adjudication_completion_rate,
    )
    payload = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
        print(str(args.output))
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
