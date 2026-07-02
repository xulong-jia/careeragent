#!/usr/bin/env python3
"""Generate an anonymized blank human review sample pack."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import random
import re
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_DIR = REPO_ROOT / "evals" / "datasets" / "anonymized_benchmark"
DEFAULT_OUTPUT = "evidence/private_outputs/human_review_sample_pack.{timestamp}.csv"
DEFAULT_SAMPLE_SIZE = 30
DEFAULT_SEED = 35
TASK_MODULES = {
    "jd_parse": "jd_parser_benchmark.jsonl",
    "resume_parse": "resume_parser_benchmark.jsonl",
    "match_score": "match_benchmark.jsonl",
    "rag_answer": "rag_answer_benchmark.jsonl",
    "project_rewrite": "project_rewrite_benchmark.jsonl",
    "agent_workflow": "agent_workflow_benchmark.jsonl",
}
CSV_FIELDS = [
    "review_batch_id",
    "dataset_name",
    "sampling_method",
    "reviewer_role",
    "privacy_sanitized",
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
]
PII_PATTERNS = [
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{8,}\d)(?!\d)"),
]


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _output_path(path: str) -> Path:
    return Path(path.format(timestamp=_timestamp()))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _assert_public_safe(value: str) -> None:
    for pattern in PII_PATTERNS:
        if pattern.search(value):
            raise ValueError("sample pack contains obvious PII")
    lowered = value.lower()
    forbidden = ["raw_text", "raw_resume", "resume_text", "jd_text", "chunk_text", "interview_answer"]
    if any(token in lowered for token in forbidden):
        raise ValueError("sample pack contains raw private field markers")


def _load_cases(dataset_dir: Path) -> dict[str, list[dict[str, Any]]]:
    cases_by_task: dict[str, list[dict[str, Any]]] = {}
    for task_type, filename in TASK_MODULES.items():
        path = dataset_dir / filename
        if not path.exists():
            raise FileNotFoundError(path)
        rows = []
        for case in _load_jsonl(path):
            if case.get("privacy_check_passed") is not True:
                continue
            note = str(case.get("anonymization_note", "")).lower()
            if not note or "synthetic only" in note:
                continue
            rows.append(case)
        if not rows:
            raise ValueError(f"no public-safe cases found for {task_type}")
        cases_by_task[task_type] = rows
    return cases_by_task


def _sample_counts(sample_size: int) -> dict[str, int]:
    task_types = list(TASK_MODULES)
    if sample_size < len(task_types):
        raise ValueError(f"sample_size must be at least {len(task_types)} to cover every task_type")
    base = sample_size // len(task_types)
    remainder = sample_size % len(task_types)
    return {
        task_type: base + (1 if index < remainder else 0)
        for index, task_type in enumerate(task_types)
    }


def build_sample_pack_rows(
    *,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    seed: int = DEFAULT_SEED,
    dataset_dir: Path = DEFAULT_DATASET_DIR,
    review_batch_id: str = "human-review-sample-pack-v35b",
) -> list[dict[str, str]]:
    rng = random.Random(seed)
    cases_by_task = _load_cases(dataset_dir)
    counts = _sample_counts(sample_size)
    rows: list[dict[str, str]] = []
    for task_type, count in counts.items():
        cases = list(cases_by_task[task_type])
        rng.shuffle(cases)
        if len(cases) < count:
            raise ValueError(f"not enough cases for {task_type}: need {count}, found {len(cases)}")
        for case in cases[:count]:
            case_id = str(case.get("case_id", "")).strip()
            if not case_id:
                raise ValueError(f"{task_type} case missing case_id")
            row = {
                "review_batch_id": review_batch_id,
                "dataset_name": "anonymized_benchmark",
                "sampling_method": f"seeded_balanced_by_task_type_seed_{seed}",
                "reviewer_role": "external_reviewer",
                "privacy_sanitized": "true",
                "item_id": f"hr_{task_type}_{case_id}",
                "task_type": task_type,
                "anonymized_input_ref": f"anonymized_benchmark:{task_type}:{case_id}:input",
                "model_output_ref": f"anonymized_benchmark:{task_type}:{case_id}:model_output",
                "reviewer_id_hash": "",
                "correctness_score": "",
                "groundedness_score": "",
                "safety_score": "",
                "usefulness_score": "",
                "privacy_risk_flag": "",
                "hallucination_flag": "",
                "fabrication_flag": "",
                "reviewer_comment": "",
                "decision": "",
                "requires_adjudication": "",
                "adjudication_decision": "",
                "bad_case_ref": "",
            }
            for value in row.values():
                _assert_public_safe(value)
            rows.append(row)
    rows.sort(key=lambda item: (item["task_type"], item["item_id"]))
    return rows


def render_csv(rows: list[dict[str, str]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rows = build_sample_pack_rows(sample_size=args.sample_size, seed=args.seed)
    payload = render_csv(rows)
    _assert_public_safe(payload)
    if args.dry_run:
        print(payload, end="")
        return 0
    output = _output_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8")
    print(str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
