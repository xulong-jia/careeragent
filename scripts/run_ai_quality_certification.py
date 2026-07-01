#!/usr/bin/env python3
"""Build an AI quality certification report from eval and proof artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path | None, default: Any) -> Any:
    if not path or not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _module_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        module: dict(bucket.get("metrics") or {})
        for module, bucket in sorted((metrics.get("by_module") or {}).items())
    }


def build_report(
    *,
    eval_dir: Path | None,
    provider_proof: Path | None,
) -> dict[str, Any]:
    metrics = _load_json(eval_dir / "metrics.json" if eval_dir else None, {})
    run_config = _load_json(eval_dir / "run_config.json" if eval_dir else None, {})
    provider = _load_json(
        provider_proof,
        {"provider_mode": "missing", "status": "missing", "proof_type": "provider"},
    )
    human = _load_json(eval_dir / "human_review_summary.json" if eval_dir else None, {})
    judge = _load_json(eval_dir / "llm_judge_summary.json" if eval_dir else None, {})
    module_metrics = _module_metrics(metrics)
    provider_mode = provider.get("provider_mode", "unknown")
    provider_verified = provider_mode == "external_verified"
    provider_signal_ok = provider.get("production_quality_candidate_signal") is True
    human_ok = float(human.get("agreement_rate", 0.0)) >= 0.8
    judge_ok = float(judge.get("hallucination_rate", 1.0)) <= 0.05
    pass_rate_ok = float(metrics.get("pass_rate", 0.0)) >= 0.95
    blockers: list[str] = []
    if not eval_dir:
        blockers.append("benchmark eval directory was not provided")
    elif not (eval_dir / "metrics.json").exists():
        blockers.append("benchmark metrics.json is missing")
    if not provider_proof:
        blockers.append("external provider proof path was not provided")
    elif not provider_proof.exists():
        blockers.append("external provider proof file is missing")
    if not provider_verified:
        blockers.append("provider proof is not external_verified")
    if provider_verified and not provider_signal_ok:
        blockers.append("provider proof does not carry production quality candidate signal")
    if not pass_rate_ok:
        blockers.append("benchmark pass_rate is below 0.95")
    if not human_ok:
        blockers.append("human review agreement is below 0.8 or missing")
    if not judge_ok:
        blockers.append("LLM judge hallucination rate is above 0.05 or missing")
    candidate = not blockers
    next_required_evidence = []
    if not provider_verified:
        next_required_evidence.append("Run external provider proof with real private env.")
    if not human_ok:
        next_required_evidence.append("Attach external human review proof with agreement >= 0.8.")
    if not pass_rate_ok:
        next_required_evidence.append("Run anonymized benchmark and provide metrics.json.")
    if not judge_ok:
        next_required_evidence.append("Attach advisory LLM judge summary with low hallucination rate.")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider_mode": provider_mode,
        "provider_proof_status": provider.get("status", "unknown"),
        "provider_proof_signal": provider_signal_ok,
        "dataset_name": run_config.get("dataset_name"),
        "dataset_kind": run_config.get("dataset_kind"),
        "benchmark_size": metrics.get("total_count", 0),
        "pass_rate": metrics.get("pass_rate", 0.0),
        "module_metrics": module_metrics,
        "human_agreement": human,
        "llm_judge_summary": judge,
        "rag_metrics": {
            "retrieval": module_metrics.get("rag_retrieval", {}),
            "answer": module_metrics.get("rag_answer", {}),
        },
        "parser_metrics": {
            "jd_parser": module_metrics.get("jd_parser", {}),
            "resume_parser": module_metrics.get("resume_parser", {}),
        },
        "match_ranking_consistency": module_metrics.get("match", {}).get(
            "ranking_consistency", 0.0
        ),
        "project_rewrite_fabrication_rate": round(
            1 - float(module_metrics.get("project_rewrite", {}).get("fabrication_guard_pass", 0.0)),
            4,
        ),
        "agent_metrics": module_metrics.get("agent_workflow", {}),
        "bad_case_regression_trend": metrics.get("bad_case_regression_trend", {}),
        "production_quality_candidate": candidate,
        "production_quality_candidate_status": (
            "candidate_with_limitations" if candidate else "blocked"
        ),
        "blockers": blockers,
        "next_required_evidence": next_required_evidence,
        "known_limitations": [
            "External provider proof is required when provider_mode is not external_verified.",
            "Committed fixtures are anonymized real-world-style cases, not private production data.",
            "LLM judge is advisory and cannot override human review.",
            "External human review and provider output artifacts must stay outside Git.",
        ],
    }


def _write_markdown(report: dict[str, Any], output_dir: Path) -> None:
    lines = [
        "# AI Quality Certification Report",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- provider_mode: {report['provider_mode']}",
        f"- dataset_name: {report['dataset_name']}",
        f"- benchmark_size: {report['benchmark_size']}",
        f"- pass_rate: {report['pass_rate']}",
        f"- human_agreement_rate: {report['human_agreement'].get('agreement_rate', 0.0)}",
        f"- llm_judge_hallucination_rate: {report['llm_judge_summary'].get('hallucination_rate', 0.0)}",
        f"- production_quality_candidate: {str(report['production_quality_candidate']).lower()}",
        f"- production_quality_candidate_status: {report['production_quality_candidate_status']}",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {item}" for item in report["blockers"] or ["none"])
    lines.extend(
        [
            "",
            "## Next Required Evidence",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["next_required_evidence"] or ["none"])
    lines.extend(
        [
            "",
            "## Known Limitations",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["known_limitations"])
    output_dir.joinpath("ai_quality_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-dir", type=Path)
    parser.add_argument("--provider-proof", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(eval_dir=args.eval_dir, provider_proof=args.provider_proof)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.output_dir.joinpath("ai_quality_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_markdown(report, args.output_dir)
    print(f"wrote {args.output_dir}")
    return 0 if report["pass_rate"] >= 0.95 else 1


if __name__ == "__main__":
    raise SystemExit(main())
