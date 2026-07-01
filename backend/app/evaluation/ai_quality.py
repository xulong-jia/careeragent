from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any


REQUIRED_HUMAN_REVIEW_FIELDS = {
    "case_id",
    "module",
    "system_score",
    "human_score",
    "human_label",
    "reviewer_confidence",
}

REQUIRED_FORMAL_HUMAN_REVIEW_FIELDS = {
    "reviewer_id",
    "review_role",
    "review_timestamp",
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

REQUIRED_LLM_JUDGE_FIELDS = {
    "case_id",
    "module",
    "rubric_version",
    "groundedness_score",
    "factuality_score",
    "completeness_score",
    "hallucination_flag",
    "evidence_alignment_score",
    "evidence_refs",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return parse_jsonl_lines(path.read_text(encoding="utf-8").splitlines())


def parse_jsonl_lines(lines: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise ValueError("JSONL records must be objects.")
        records.append(parsed)
    return records


def parse_human_review_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    for record in records:
        missing = REQUIRED_HUMAN_REVIEW_FIELDS - set(record)
        if missing:
            raise ValueError(f"Human review record missing fields: {sorted(missing)}")
        parsed.append(
            {
                "case_id": str(record["case_id"]),
                "module": str(record["module"]),
                "system_score": float(record["system_score"]),
                "human_score": float(record["human_score"]),
                "human_label": str(record["human_label"]),
                "reviewer_confidence": float(record["reviewer_confidence"]),
                "disagreement_reason": str(record.get("disagreement_reason") or ""),
                "accepted_strengths": list(record.get("accepted_strengths") or []),
                "missed_gaps": list(record.get("missed_gaps") or []),
                "overclaim_flags": list(record.get("overclaim_flags") or []),
            }
        )
    return parsed


def parse_formal_human_review_records(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    for record in records:
        missing = REQUIRED_FORMAL_HUMAN_REVIEW_FIELDS - set(record)
        if missing:
            raise ValueError(f"Formal human review record missing fields: {sorted(missing)}")
        parsed.append(
            {
                "reviewer_id": str(record["reviewer_id"]),
                "review_role": str(record["review_role"]),
                "review_timestamp": str(record["review_timestamp"]),
                "rubric_version": str(record["rubric_version"]),
                "module": str(record["module"]),
                "case_id": str(record["case_id"]),
                "human_score": float(record["human_score"]),
                "human_label": str(record["human_label"]),
                "confidence": float(record["confidence"]),
                "disagreement_reason": str(record.get("disagreement_reason") or ""),
                "accepted_output": bool(record["accepted_output"]),
                "rejected_output": bool(record["rejected_output"]),
                "correction_note": str(record["correction_note"]),
                "privacy_review_passed": bool(record["privacy_review_passed"]),
                "adjudication_status": str(record.get("adjudication_status") or "pending"),
            }
        )
    return parsed


def compute_two_reviewer_agreement(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_case: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_case.setdefault(str(record["case_id"]), []).append(record)

    comparable = [case_records for case_records in by_case.values() if len(case_records) >= 2]
    agreements = 0
    disagreements: list[dict[str, Any]] = []
    for case_records in comparable:
        first, second = case_records[0], case_records[1]
        score_delta = abs(float(first["human_score"]) - float(second["human_score"]))
        label_match = first["human_label"] == second["human_label"]
        accepted_match = first["accepted_output"] == second["accepted_output"]
        if score_delta <= 10 and label_match and accepted_match:
            agreements += 1
        else:
            disagreements.append(
                {
                    "case_id": first["case_id"],
                    "module": first["module"],
                    "score_delta": round(score_delta, 4),
                    "labels": [first["human_label"], second["human_label"]],
                    "adjudication_status": first.get("adjudication_status", "pending"),
                }
            )

    confidence_values = [float(record["confidence"]) for record in records]
    privacy_failures = [
        record["case_id"] for record in records if not record["privacy_review_passed"]
    ]
    return {
        "reviewed_count": len(records),
        "case_count": len(by_case),
        "two_reviewer_case_count": len(comparable),
        "agreement_rate": round(agreements / len(comparable), 4) if comparable else 0.0,
        "disagreement_cases": disagreements,
        "privacy_review_passed": not privacy_failures,
        "privacy_failure_case_ids": privacy_failures,
        "reviewer_confidence_average": round(mean(confidence_values), 4)
        if confidence_values
        else 0.0,
    }


def parse_llm_judge_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    for record in records:
        missing = REQUIRED_LLM_JUDGE_FIELDS - set(record)
        if missing:
            raise ValueError(f"LLM judge record missing fields: {sorted(missing)}")
        evidence_refs = [str(item) for item in record.get("evidence_refs") or []]
        parsed.append(
            {
                "case_id": str(record["case_id"]),
                "module": str(record["module"]),
                "rubric_version": str(record["rubric_version"]),
                "groundedness_score": float(record["groundedness_score"]),
                "factuality_score": float(record["factuality_score"]),
                "completeness_score": float(record["completeness_score"]),
                "hallucination_flag": bool(record["hallucination_flag"]),
                "evidence_alignment_score": float(record["evidence_alignment_score"])
                if evidence_refs
                else 0.0,
                "evidence_refs": evidence_refs,
                "judge_model": str(record.get("judge_model") or "unknown"),
            }
        )
    return parsed


def compute_llm_judge_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {
            "judged_count": 0,
            "groundedness_score": 0.0,
            "factuality_score": 0.0,
            "completeness_score": 0.0,
            "evidence_alignment_score": 0.0,
            "hallucination_rate": 0.0,
            "no_evidence_judgment_count": 0,
        }
    return {
        "judged_count": len(records),
        "groundedness_score": round(mean(item["groundedness_score"] for item in records), 4),
        "factuality_score": round(mean(item["factuality_score"] for item in records), 4),
        "completeness_score": round(mean(item["completeness_score"] for item in records), 4),
        "evidence_alignment_score": round(
            mean(item["evidence_alignment_score"] for item in records), 4
        ),
        "hallucination_rate": round(
            sum(1 for item in records if item["hallucination_flag"]) / len(records), 4
        ),
        "no_evidence_judgment_count": sum(
            1 for item in records if not item["evidence_refs"]
        ),
    }


def compute_match_calibration(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {
            "reviewed_count": 0,
            "mean_absolute_score_delta": 0.0,
            "disagreement_rate": 0.0,
            "human_agreement_rate": 0.0,
            "ranking_consistency": 0.0,
            "score_distribution": {},
            "dimension_disagreement": {},
        }
    deltas = [abs(record["system_score"] - record["human_score"]) for record in records]
    disagreements = [
        record
        for record in records
        if abs(record["system_score"] - record["human_score"]) >= 10
        or record["human_label"] in {"reject", "major_gap"}
    ]
    return {
        "reviewed_count": len(records),
        "mean_absolute_score_delta": round(mean(deltas), 4),
        "disagreement_rate": round(len(disagreements) / len(records), 4),
        "human_agreement_rate": round(1 - (len(disagreements) / len(records)), 4),
        "ranking_consistency": _ranking_consistency(records),
        "score_distribution": _score_distribution(records),
        "dimension_disagreement": _dimension_disagreement(records),
    }


def score_stability(
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
) -> dict[str, Any]:
    after_by_case = {str(item.get("case_id")): item for item in after}
    deltas: list[float] = []
    changed_cases: list[str] = []
    for item in before:
        case_id = str(item.get("case_id"))
        if case_id not in after_by_case:
            continue
        delta = abs(
            float(item.get("score", 0.0)) - float(after_by_case[case_id].get("score", 0.0))
        )
        deltas.append(delta)
        if delta > 5:
            changed_cases.append(case_id)
    return {
        "compared_count": len(deltas),
        "max_score_delta": round(max(deltas), 4) if deltas else 0.0,
        "mean_score_delta": round(mean(deltas), 4) if deltas else 0.0,
        "changed_case_ids": changed_cases,
    }


def failed_case_to_bad_case_candidate(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_type": "evaluation_case",
        "source_id": str(result.get("case_id") or ""),
        "module": str(result.get("module") or "unknown"),
        "category": str(result.get("failure_type") or "ai_quality_regression"),
        "severity": "medium",
        "summary": str(result.get("failure_reason") or result.get("error") or ""),
        "privacy_safe": True,
    }


def bad_case_regression_trend(
    failed_cases: list[dict[str, Any]],
    *,
    reopened_case_count: int = 0,
) -> dict[str, Any]:
    total = len(failed_cases) + reopened_case_count
    resolved = len(failed_cases)
    return {
        "candidate_count": len(failed_cases),
        "reopened_case_count": reopened_case_count,
        "regression_pass_rate": round(1 - (reopened_case_count / total), 4)
        if total
        else 1.0,
        "bad_case_candidates": [
            failed_case_to_bad_case_candidate(item) for item in failed_cases[:20]
        ],
        "resolved_failed_case_count": resolved,
    }


def _ranking_consistency(records: list[dict[str, Any]]) -> float:
    system_order = sorted(records, key=lambda item: (-item["system_score"], item["case_id"]))
    human_order = sorted(records, key=lambda item: (-item["human_score"], item["case_id"]))
    if not system_order:
        return 0.0
    matches = sum(
        1
        for index, record in enumerate(system_order)
        if human_order[index]["case_id"] == record["case_id"]
    )
    return round(matches / len(system_order), 4)


def _score_distribution(records: list[dict[str, Any]]) -> dict[str, int]:
    buckets = {"0-49": 0, "50-69": 0, "70-84": 0, "85-100": 0}
    for record in records:
        score = record["system_score"]
        if score < 50:
            buckets["0-49"] += 1
        elif score < 70:
            buckets["50-69"] += 1
        elif score < 85:
            buckets["70-84"] += 1
        else:
            buckets["85-100"] += 1
    return buckets


def _dimension_disagreement(records: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "missed_gap_count": sum(len(record["missed_gaps"]) for record in records),
        "overclaim_flag_count": sum(len(record["overclaim_flags"]) for record in records),
        "low_confidence_review_count": sum(
            1 for record in records if record["reviewer_confidence"] < 0.75
        ),
    }
