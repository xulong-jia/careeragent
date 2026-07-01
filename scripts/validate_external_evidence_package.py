#!/usr/bin/env python3
"""Validate v3.5 private evidence outputs without exposing private artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = REPO_ROOT / "evidence" / "schemas"
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]+"),
    re.compile(r"ghp_[A-Za-z0-9_]+"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(authorization|api[_-]?key|token|secret)[\"'=:\s]+[A-Za-z0-9_./+=-]{12,}"),
]
REQUIRED_CANDIDATE_PROOFS = [
    "provider",
    "human_review",
    "deployment",
    "backup_purge",
    "monitoring",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_schemas() -> dict[str, dict[str, Any]]:
    schemas: dict[str, dict[str, Any]] = {}
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        proof_type = schema.get("properties", {}).get("proof_type", {}).get("const")
        if proof_type:
            schemas[proof_type] = schema
    return schemas


def _has_secret(raw: str) -> bool:
    return any(pattern.search(raw) for pattern in SECRET_PATTERNS)


def _validate_required(payload: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in schema.get("required", []):
        if field not in payload:
            errors.append(f"missing required field: {field}")
    expected_type = schema.get("properties", {}).get("proof_type", {}).get("const")
    if expected_type and payload.get("proof_type") != expected_type:
        errors.append(f"proof_type must be {expected_type}")
    return errors


def _proofs_by_type(artifacts: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_type: dict[str, list[dict[str, Any]]] = {}
    for artifact in artifacts:
        proof_type = str(artifact.get("proof_type", ""))
        by_type.setdefault(proof_type, []).append(artifact)
    return by_type


def _provider_ok(proofs: list[dict[str, Any]]) -> bool:
    for proof in proofs:
        if all(
            [
                proof.get("provider_mode") == "provider_verified",
                proof.get("embedding_validation_passed") is True,
                proof.get("llm_validation_passed") is True,
                proof.get("timeout_retry_validation") is True,
                proof.get("schema_validation_passed") is True,
                proof.get("rag_grounded_answer_sample_passed") is True,
                proof.get("llm_judge_sample_passed") is True,
                proof.get("secret_leak_check_passed") is True,
                proof.get("production_quality_candidate_signal") is True,
            ]
        ):
            return True
    return False


def _human_review_ok(proofs: list[dict[str, Any]]) -> bool:
    return any(
        proof.get("reviewer_count", 0) >= 2
        and proof.get("case_count", 0) > 0
        and proof.get("agreement_rate", 0) >= 0.8
        and proof.get("privacy_review_passed") is True
        for proof in proofs
    )


def _deployment_ok(proofs: list[dict[str, Any]]) -> bool:
    fields = [
        "cloud_deployment_validation_passed",
        "managed_db_validation_passed",
        "secret_manager_validation_passed",
        "kms_validation_passed",
        "tls_validation_passed",
        "readiness_validation_passed",
        "rollback_validation_passed",
    ]
    return any(all(proof.get(field) is True for field in fields) for proof in proofs)


def _backup_purge_ok(proofs: list[dict[str, Any]]) -> bool:
    return any(
        proof.get("backup_purge_status") == "complete"
        and proof.get("restore_block_rule_verified") is True
        for proof in proofs
    )


def _monitoring_ok(proofs: list[dict[str, Any]]) -> bool:
    return any(
        proof.get("metrics_backend")
        and proof.get("log_drain")
        and proof.get("tracing_backend")
        and proof.get("error_reporting")
        and proof.get("alert_rules_verified") is True
        and proof.get("privacy_redaction_verified") is True
        and proof.get("incident_runbook_verified") is True
        for proof in proofs
    )


def _security_review_ok(proofs: list[dict[str, Any]]) -> bool:
    return any(
        proof.get("critical_findings_open") == 0
        and proof.get("high_findings_open") == 0
        and proof.get("privacy_review_passed") is True
        and proof.get("remediation_plan_attached") is True
        for proof in proofs
    )


def validate_evidence_package(evidence_dir: Path) -> dict[str, Any]:
    schemas = _load_schemas()
    artifacts: list[dict[str, Any]] = []
    invalid_artifacts: list[dict[str, Any]] = []
    leaked_artifacts: list[str] = []

    json_paths = sorted(evidence_dir.glob("*.json")) if evidence_dir.exists() else []
    for path in json_paths:
        raw = path.read_text(encoding="utf-8")
        if _has_secret(raw):
            leaked_artifacts.append(path.name)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            invalid_artifacts.append({"path": path.name, "errors": [str(exc)]})
            continue
        schema = schemas.get(str(payload.get("proof_type", "")))
        if not schema:
            invalid_artifacts.append(
                {"path": path.name, "errors": ["unknown or missing proof_type"]}
            )
            continue
        errors = _validate_required(payload, schema)
        if errors:
            invalid_artifacts.append({"path": path.name, "errors": errors})
            continue
        artifacts.append(payload)

    by_type = _proofs_by_type(artifacts)
    missing_external_proofs = [
        proof_type for proof_type in REQUIRED_CANDIDATE_PROOFS if proof_type not in by_type
    ]
    candidate_blockers = [f"missing external proof: {item}" for item in missing_external_proofs]
    if invalid_artifacts:
        candidate_blockers.append("invalid evidence artifacts must be fixed")
    if leaked_artifacts:
        candidate_blockers.append("secret-like material detected in evidence artifacts")
    if by_type.get("provider") and not _provider_ok(by_type["provider"]):
        candidate_blockers.append("provider proof is not externally verified end-to-end")
    if by_type.get("human_review") and not _human_review_ok(by_type["human_review"]):
        candidate_blockers.append("human review proof lacks reviewer agreement/privacy pass")
    if by_type.get("deployment") and not _deployment_ok(by_type["deployment"]):
        candidate_blockers.append("deployment proof lacks cloud/DB/KMS/readiness/rollback pass")
    if by_type.get("backup_purge") and not _backup_purge_ok(by_type["backup_purge"]):
        candidate_blockers.append("backup purge proof is not complete")
    if by_type.get("monitoring") and not _monitoring_ok(by_type["monitoring"]):
        candidate_blockers.append("monitoring proof lacks observability/privacy/incident pass")

    certified_blockers = list(candidate_blockers)
    if "security_review" not in by_type:
        certified_blockers.append("missing external proof: security_review")
    elif not _security_review_ok(by_type["security_review"]):
        certified_blockers.append("external security review proof is not clean")

    return {
        "generated_at": _utc_now(),
        "evidence_dir": str(evidence_dir),
        "artifact_count": len(json_paths),
        "valid_artifact_count": len(artifacts),
        "proof_types_found": sorted(key for key in by_type if key),
        "schema_validation_passed": not invalid_artifacts,
        "secret_leak_check_passed": not leaked_artifacts,
        "invalid_artifacts": invalid_artifacts,
        "secret_leak_artifacts": leaked_artifacts,
        "missing_external_proofs": missing_external_proofs,
        "candidate_blockers": candidate_blockers,
        "certified_blockers": certified_blockers,
        "production_ready_candidate_possible": not candidate_blockers,
        "production_readiness_certified_possible": not certified_blockers,
        "boundary": (
            "This validator checks redacted external evidence shapes and blocker signals. "
            "It does not create production proof by itself."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    summary = validate_evidence_package(args.evidence_dir)
    payload = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
        print(str(args.output))
    else:
        print(payload, end="")
    if not summary["schema_validation_passed"] or not summary["secret_leak_check_passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
