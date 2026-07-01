from __future__ import annotations

import csv
import json
from pathlib import Path
import subprocess

from scripts import import_human_review_proof
from scripts import run_external_provider_proof
from scripts import validate_external_evidence_package


ROOT = Path(__file__).resolve().parents[2]


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_evidence_templates_match_schema_required_fields():
    for schema_path in sorted((ROOT / "evidence" / "schemas").glob("*.schema.json")):
        schema = _json(schema_path)
        template_path = (
            ROOT
            / "evidence"
            / "templates"
            / schema_path.name.replace(".schema.json", ".template.json")
        )
        assert template_path.exists(), template_path
        template = _json(template_path)
        for field in schema["required"]:
            assert field in template, f"{field} missing from {template_path.name}"


def test_human_review_input_template_has_required_columns():
    template = ROOT / "evidence" / "templates" / "human_review_input.template.csv"
    with template.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert import_human_review_proof.REQUIRED_FIELDS <= set(reader.fieldnames or [])


def test_private_outputs_are_gitignored():
    result = subprocess.run(
        ["git", "check-ignore", "-q", "evidence/private_outputs/test.json"],
        cwd=ROOT,
        check=False,
    )
    assert result.returncode == 0


def test_provider_dry_run_is_not_production_proof(monkeypatch):
    secret = "provider-token-redact-value-123"
    monkeypatch.setenv("LLM_API_KEY", secret)

    proof = run_external_provider_proof.build_external_provider_proof(
        dry_run=True,
        provider="openai_compatible",
        embedding_model="text-embedding-test",
        llm_model="chat-test",
    )
    rendered = json.dumps(proof)

    assert proof["provider_mode"] == "not_verified"
    assert proof["production_quality_candidate_signal"] is False
    assert proof["secret_leak_check_passed"] is True
    assert secret not in rendered


def test_human_review_import_redacts_reviewers_and_computes_agreement(tmp_path):
    input_path = tmp_path / "reviews.csv"
    rows = [
        {
            "reviewer_id": "reviewer_a@example.invalid",
            "rubric_version": "human-review-v3.5",
            "module": "match",
            "case_id": "case_1",
            "human_score": "84",
            "human_label": "accept",
            "confidence": "0.9",
            "accepted_output": "true",
            "rejected_output": "false",
            "correction_note": "",
            "privacy_review_passed": "true",
            "adjudication_status": "",
        },
        {
            "reviewer_id": "reviewer_b@example.invalid",
            "rubric_version": "human-review-v3.5",
            "module": "match",
            "case_id": "case_1",
            "human_score": "82",
            "human_label": "accept",
            "confidence": "0.8",
            "accepted_output": "true",
            "rejected_output": "false",
            "correction_note": "",
            "privacy_review_passed": "true",
            "adjudication_status": "",
        },
    ]
    with input_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    proof = import_human_review_proof.build_human_review_proof(
        input_path,
        batch_id="review-batch-test",
    )
    rendered = json.dumps(proof)

    assert proof["reviewer_count"] == 2
    assert proof["agreement_rate"] == 1.0
    assert proof["privacy_review_passed"] is True
    assert "reviewer_a@example.invalid" not in rendered
    assert all(item.startswith("reviewer:") for item in proof["reviewer_ids_redacted"])


def test_evidence_validator_blocks_missing_external_proofs(tmp_path):
    summary = validate_external_evidence_package.validate_evidence_package(tmp_path)

    assert summary["production_ready_candidate_possible"] is False
    assert "provider" in summary["missing_external_proofs"]
    assert "security_review" in summary["certified_blockers"][-1]


def test_evidence_validator_accepts_complete_redacted_package(tmp_path):
    proofs = [
        {
            "proof_type": "provider",
            "proof_id": "provider-proof-test",
            "created_at": "2026-07-02T00:00:00Z",
            "provider": "openai_compatible",
            "provider_mode": "provider_verified",
            "base_url_redacted": "[set length=20 sha256:abcdef123456]",
            "embedding_model": "embedding-model",
            "llm_model": "llm-model",
            "embedding_validation_passed": True,
            "llm_validation_passed": True,
            "timeout_retry_validation": True,
            "schema_validation_passed": True,
            "rag_grounded_answer_sample_passed": True,
            "llm_judge_sample_passed": True,
            "secret_leak_check_passed": True,
            "production_quality_candidate_signal": True,
            "limitations": [],
        },
        {
            "proof_type": "human_review",
            "review_batch_id": "human-review-test",
            "generated_at": "2026-07-02T00:00:00Z",
            "reviewer_count": 2,
            "reviewer_ids_redacted": ["reviewer:aaaa", "reviewer:bbbb"],
            "rubric_version": "human-review-v3.5",
            "case_count": 40,
            "modules_covered": ["match", "rag"],
            "agreement_rate": 0.85,
            "adjudication_required_count": 0,
            "privacy_review_passed": True,
            "limitations": [],
        },
        {
            "proof_type": "deployment",
            "proof_id": "deployment-proof-test",
            "created_at": "2026-07-02T00:00:00Z",
            "provider": "cloud",
            "region": "region",
            "service": "careeragent",
            "git_commit": "abcdef",
            "cloud_deployment_validation_passed": True,
            "managed_db_validation_passed": True,
            "secret_manager_validation_passed": True,
            "kms_validation_passed": True,
            "tls_validation_passed": True,
            "readiness_validation_passed": True,
            "rollback_validation_passed": True,
            "proof_artifacts_redacted": ["redacted-runbook-ref"],
            "limitations": [],
        },
        {
            "proof_type": "backup_purge",
            "proof_id": "backup-purge-test",
            "created_at": "2026-07-02T00:00:00Z",
            "deletion_proof_id": "delete-proof-test",
            "affected_backup_ids_redacted": ["backup:redacted"],
            "backup_purge_status": "complete",
            "legal_hold_status": "none",
            "restore_block_rule_verified": True,
            "audit_artifact_redacted": "redacted-audit-ref",
            "limitations": [],
        },
        {
            "proof_type": "monitoring",
            "proof_id": "monitoring-proof-test",
            "created_at": "2026-07-02T00:00:00Z",
            "metrics_backend": "managed-metrics",
            "log_drain": "managed-logs",
            "tracing_backend": "managed-tracing",
            "error_reporting": "managed-errors",
            "alert_rules_verified": True,
            "privacy_redaction_verified": True,
            "incident_runbook_verified": True,
            "limitations": [],
        },
        {
            "proof_type": "security_review",
            "proof_id": "security-review-test",
            "created_at": "2026-07-02T00:00:00Z",
            "reviewer_redacted": "external-reviewer",
            "scope": ["api", "auth", "deployment"],
            "critical_findings_open": 0,
            "high_findings_open": 0,
            "privacy_review_passed": True,
            "remediation_plan_attached": True,
            "limitations": [],
        },
    ]
    for proof in proofs:
        (tmp_path / f"{proof['proof_type']}.json").write_text(
            json.dumps(proof),
            encoding="utf-8",
        )

    summary = validate_external_evidence_package.validate_evidence_package(tmp_path)

    assert summary["schema_validation_passed"] is True
    assert summary["secret_leak_check_passed"] is True
    assert summary["production_ready_candidate_possible"] is True
    assert summary["production_readiness_certified_possible"] is True


def test_templates_do_not_contain_secret_like_material():
    rendered = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "evidence" / "templates").glob("*"))
    )
    assert validate_external_evidence_package.SECRET_PATTERNS
    assert not any(
        pattern.search(rendered)
        for pattern in validate_external_evidence_package.SECRET_PATTERNS
    )
