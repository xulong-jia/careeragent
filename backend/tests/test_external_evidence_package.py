from __future__ import annotations

import csv
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import subprocess
import threading

from scripts import check_provider_proof_readiness
from scripts import import_human_review_proof
from scripts import run_ai_quality_certification
from scripts import run_external_provider_proof
from scripts import validate_external_evidence_package


ROOT = Path(__file__).resolve().parents[2]


class _FakeProviderHandler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        prompt = json.dumps(payload)
        if self.path.endswith("/embeddings"):
            body = {"data": [{"embedding": [0.1, 0.2, 0.3, 0.4]}]}
        elif "grounded=true" in prompt:
            body = {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "answer": "CareerAgent requires redacted provider proof.",
                                    "citations": ["chunk_safe_1"],
                                    "grounded": True,
                                }
                            )
                        }
                    }
                ]
            }
        elif "advisory judge" in prompt:
            body = {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "groundedness_score": 1.0,
                                    "factuality_score": 1.0,
                                    "hallucination_flag": False,
                                    "evidence_refs": ["chunk_safe_1"],
                                }
                            )
                        }
                    }
                ]
            }
        else:
            body = {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "job_profile_id": "provider_probe",
                                    "job_title": "Backend Engineer",
                                    "company": "Anonymized Company",
                                    "role_category": "backend",
                                    "required_skills": ["Python"],
                                    "preferred_skills": ["FastAPI"],
                                    "parse_confidence": 0.91,
                                }
                            )
                        }
                    }
                ]
            }
        raw = json.dumps(body).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *_args):
        return


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_quality_inputs(tmp_path: Path) -> Path:
    eval_dir = tmp_path / "eval"
    eval_dir.mkdir()
    (eval_dir / "metrics.json").write_text(
        json.dumps({"total_count": 155, "pass_rate": 1.0, "by_module": {}}),
        encoding="utf-8",
    )
    (eval_dir / "run_config.json").write_text(
        json.dumps({"dataset_name": "anonymized_benchmark", "dataset_kind": "benchmark"}),
        encoding="utf-8",
    )
    (eval_dir / "human_review_summary.json").write_text(
        json.dumps({"agreement_rate": 0.85}),
        encoding="utf-8",
    )
    (eval_dir / "llm_judge_summary.json").write_text(
        json.dumps({"hallucination_rate": 0.0}),
        encoding="utf-8",
    )
    return eval_dir


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


def test_provider_readiness_checker_reports_missing_env():
    report = check_provider_proof_readiness.build_readiness_report(env={})

    assert report["readiness_status"] == "missing_required_env"
    assert "LLM_API_KEY" in report["missing_vars"]
    assert report["secret_leak_check_passed"] is True


def test_provider_readiness_checker_masks_present_env():
    env = {
        "AI_PROVIDER_MODE": "provider_verified",
        "LLM_PROVIDER": "openai_compatible",
        "LLM_BASE_URL": "https://provider.example.invalid/v1",
        "LLM_MODEL": "chat-real",
        "LLM_API_KEY": "private-llm-key-value-12345",
        "EMBEDDING_PROVIDER": "openai_compatible",
        "EMBEDDING_BASE_URL": "https://embedding.example.invalid/v1",
        "EMBEDDING_MODEL": "embedding-real",
        "EMBEDDING_API_KEY": "private-embedding-key-value-12345",
        "DATA_ENCRYPTION_KEY": "private-data-key-value-12345",
        "AUTH_JWT_SECRET": "private-auth-secret-value-12345",
    }

    report = check_provider_proof_readiness.build_readiness_report(env=env)
    rendered = json.dumps(report)

    assert report["readiness_status"] == "ready"
    assert report["missing_vars"] == []
    assert "private-llm-key-value-12345" not in rendered
    assert "private-embedding-key-value-12345" not in rendered
    assert report["masked_config_summary"]["LLM_API_KEY"]["value"].startswith("[set length=")


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

    assert proof["provider_mode"] == "dry_run"
    assert proof["production_quality_candidate_signal"] is False
    assert proof["secret_leak_check_passed"] is True
    assert secret not in rendered


def test_provider_fake_server_is_marked_fake_not_external(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), _FakeProviderHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        monkeypatch.setenv("LLM_API_KEY", "test-provider-key")
        monkeypatch.setenv("EMBEDDING_API_KEY", "test-embedding-key")
        monkeypatch.setenv("EMBEDDING_DIMENSION", "4")

        proof = run_external_provider_proof.build_external_provider_proof(
            dry_run=False,
            provider="openai_compatible",
            llm_base_url=base_url,
            embedding_base_url=base_url,
            embedding_model="fake-embedding",
            llm_model="fake-chat",
        )
        rendered = json.dumps(proof)

        assert proof["provider_mode"] == "fake"
        assert proof["llm_validation_passed"] is True
        assert proof["embedding_validation_passed"] is True
        assert proof["rag_grounded_answer_sample_passed"] is True
        assert proof["llm_judge_sample_passed"] is True
        assert proof["production_quality_candidate_signal"] is False
        assert "test-provider-key" not in rendered
    finally:
        server.shutdown()
        thread.join(timeout=2)


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
            "provider_mode": "external_verified",
            "llm_provider": "openai_compatible",
            "embedding_provider": "openai_compatible",
            "base_url_redacted": {
                "llm": "[set length=20 sha256:abcdef123456]",
                "embedding": "[set length=22 sha256:abcdef123456]",
            },
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


def test_ai_quality_certification_rejects_missing_provider_proof(tmp_path):
    eval_dir = _write_quality_inputs(tmp_path)

    report = run_ai_quality_certification.build_report(
        eval_dir=eval_dir,
        provider_proof=None,
    )

    assert report["production_quality_candidate"] is False
    assert "external provider proof path was not provided" in report["blockers"]


def test_ai_quality_certification_rejects_offline_provider_proof(tmp_path):
    eval_dir = _write_quality_inputs(tmp_path)
    proof_path = tmp_path / "provider.json"
    proof_path.write_text(
        json.dumps({"proof_type": "provider", "provider_mode": "not_verified"}),
        encoding="utf-8",
    )

    report = run_ai_quality_certification.build_report(
        eval_dir=eval_dir,
        provider_proof=proof_path,
    )

    assert report["production_quality_candidate"] is False
    assert "provider proof is not external_verified" in report["blockers"]


def test_ai_quality_certification_accepts_test_external_verified_proof(tmp_path):
    eval_dir = _write_quality_inputs(tmp_path)
    proof_path = tmp_path / "provider.json"
    proof_path.write_text(
        json.dumps(
            {
                "proof_type": "provider",
                "provider_mode": "external_verified",
                "production_quality_candidate_signal": True,
            }
        ),
        encoding="utf-8",
    )

    report = run_ai_quality_certification.build_report(
        eval_dir=eval_dir,
        provider_proof=proof_path,
    )

    assert report["production_quality_candidate"] is True
    assert report["production_quality_candidate_status"] == "candidate_with_limitations"
    assert report["blockers"] == []


def test_provider_docs_commands_match_cli_arguments():
    docs = "\n".join(
        [
            (ROOT / "docs" / "provider-proof-runbook.md").read_text(encoding="utf-8"),
            (ROOT / "docs" / "external-production-evidence-package.md").read_text(
                encoding="utf-8"
            ),
            (ROOT / "README.md").read_text(encoding="utf-8"),
        ]
    )
    help_result = subprocess.run(
        [
            "python3",
            "scripts/run_external_provider_proof.py",
            "--help",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    help_text = help_result.stdout
    for flag in ["--llm-base-url", "--embedding-base-url", "--redact", "--fail-on-not-verified"]:
        assert flag in docs
        assert flag in help_text
    assert "scripts/check_provider_proof_readiness.py" in docs


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
