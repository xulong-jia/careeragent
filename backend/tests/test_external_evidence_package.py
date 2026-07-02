from __future__ import annotations

import csv
from http.server import BaseHTTPRequestHandler, HTTPServer
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import threading
import zipfile

import pytest

from scripts import check_provider_proof_readiness
from scripts import create_external_ops_proof_template
from scripts import generate_human_review_sample_pack
from scripts import import_human_review_batch
from scripts import import_human_review_proof
from scripts import merge_human_review_batches
from scripts import run_ai_quality_certification
from scripts import run_external_provider_proof
from scripts import summarize_human_review_evidence
from scripts import validate_external_evidence_package


ROOT = Path(__file__).resolve().parents[2]


class _FakeProviderHandler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("content-length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        prompt = json.dumps(payload)
        if self.path.endswith("/embeddings"):
            body = {"data": [{"embedding": [0.1, 0.2, 0.3, 0.4]}]}
        elif "CareerAgent requires redacted provider proof" in prompt:
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
        elif "groundedness_score" in prompt:
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


def _jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


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


def _human_review_row(
    index: int,
    *,
    reviewer: str = "reviewer:external_a",
    decision: str = "pass",
    hallucination: bool = False,
    fabrication: bool = False,
    privacy_risk: bool = False,
    requires_adjudication: bool = False,
    adjudication_decision: str = "",
) -> dict:
    return {
        "review_batch_id": "human-review-test",
        "dataset_name": "anonymized_external_review_test",
        "sampling_method": "stratified_by_task_type_and_risk",
        "reviewer_role": "external_ai_quality_reviewer",
        "privacy_sanitized": "true",
        "item_id": f"item_{index:03d}",
        "task_type": "rag_answer",
        "anonymized_input_ref": f"case_ref_{index:03d}",
        "model_output_ref": f"output_ref_{index:03d}",
        "reviewer_id_hash": reviewer,
        "correctness_score": "0.95",
        "groundedness_score": "0.95",
        "safety_score": "1.0",
        "usefulness_score": "0.9",
        "privacy_risk_flag": str(privacy_risk).lower(),
        "hallucination_flag": str(hallucination).lower(),
        "fabrication_flag": str(fabrication).lower(),
        "reviewer_comment": "anonymized synthetic test row",
        "decision": decision,
        "requires_adjudication": str(requires_adjudication).lower(),
        "adjudication_decision": adjudication_decision,
        "bad_case_ref": "bad_case_001" if decision in {"major_issue", "fail"} else "",
    }


def _write_human_review_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _assert_readable_review_context(row: dict[str, str]) -> None:
    input_summary = row.get("input_summary") or row.get("输入摘要（匿名）", "")
    output_summary = row.get("model_output_summary") or row.get("模型输出摘要", "")
    instruction = row.get("review_instruction") or row.get("审核说明", "")

    for value in [input_summary, output_summary]:
        assert len(value) >= 40
    assert len(instruction) >= 20
    assert "判断" in instruction or "检查" in instruction
    ref_only_markers = ["input_ref=", "expected_output_ref=", "signals={"]
    assert not any(marker in input_summary for marker in ref_only_markers)
    assert not any(marker in output_summary for marker in ref_only_markers)
    assert "Synthetic/anonymized review sample" in input_summary


def _xlsx_workbook_xml(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        return "\n".join(
            archive.read(name).decode("utf-8")
            for name in archive.namelist()
            if name.startswith("xl/")
        )


def _xlsx_card_rows(path: Path) -> list[dict[str, str]]:
    rows_by_sheet = import_human_review_batch._xlsx_rows_by_name(path)
    raw_rows = rows_by_sheet["审核卡片"]
    cards: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for raw_row in raw_rows:
        if not any(str(value).strip() for value in raw_row):
            continue
        label = import_human_review_batch._normalize_card_label(raw_row[0] if raw_row else "")
        value = str(raw_row[1]).strip() if len(raw_row) > 1 else ""
        if label.startswith("样本 "):
            if current.get("item_id"):
                cards.append(current)
            current = {}
            continue
        field = import_human_review_batch.XLSX_CARD_LABEL_TO_FIELD.get(label)
        if field:
            current[field] = value
    if current.get("item_id"):
        cards.append(current)
    return cards


def _assert_xlsx_has_no_complex_ooxml(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
    workbook_xml = _xlsx_workbook_xml(path)
    assert not re.search(r"<f(?:\s|>)", workbook_xml)
    for marker in generate_human_review_sample_pack.FORBIDDEN_XLSX_XML_MARKERS:
        assert marker not in workbook_xml
        assert not any(marker in name for name in names)


def _human_review_batch_payload(sample_size: int = 30) -> dict:
    rows = [
        _human_review_row(
            index,
            reviewer="reviewer:external_a" if index % 2 else "reviewer:external_b",
        )
        for index in range(1, sample_size + 1)
    ]
    items = import_human_review_batch.normalize_review_items(rows)
    summary = import_human_review_batch.summarize_items(items)
    return {
        "proof_type": "human_review",
        "review_batch_id": "human-review-test",
        "created_at": "2026-07-02T00:00:00Z",
        "reviewer_count": 2,
        "reviewer_roles": ["external_ai_quality_reviewer"],
        "dataset_name": "anonymized_external_review_test",
        "sample_size": sample_size,
        "sampling_method": "stratified_by_task_type_and_risk",
        "privacy_sanitized": True,
        "review_items": items,
        "agreement_metrics": {
            "comparable_item_count": 0,
            "decision_agreement_rate": 0.0,
        },
        "adjudication_required_count": summary["adjudication_required_count"],
        "adjudication_completed_count": summary["adjudication_completed_count"],
        "bad_case_count": summary["bad_case_count"],
        "summary": summary,
        "production_quality_candidate_signal": True,
        "limitations": [],
    }


def _single_reviewer_human_review_batch(reviewer: str, sample_size: int = 30) -> dict:
    rows = [
        _human_review_row(index, reviewer=reviewer)
        for index in range(1, sample_size + 1)
    ]
    items = import_human_review_batch.normalize_review_items(rows)
    summary = import_human_review_batch.summarize_items(items)
    return {
        "proof_type": "human_review",
        "review_batch_id": f"human-review-{reviewer.replace(':', '-')}",
        "created_at": "2026-07-02T00:00:00Z",
        "reviewer_count": 1,
        "reviewer_roles": ["external_ai_quality_reviewer"],
        "dataset_name": "anonymized_external_review_test",
        "sample_size": sample_size,
        "sampling_method": "stratified_by_task_type_and_risk",
        "privacy_sanitized": True,
        "review_items": items,
        "agreement_metrics": {
            "comparable_item_count": 0,
            "decision_agreement_rate": 0.0,
        },
        "adjudication_required_count": summary["adjudication_required_count"],
        "adjudication_completed_count": summary["adjudication_completed_count"],
        "bad_case_count": summary["bad_case_count"],
        "summary": summary,
        "production_quality_candidate_signal": False,
        "limitations": ["At least two independent reviewers are required."],
    }


def _provider_proof_payload() -> dict:
    return {
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
    }


def _ops_proof_payload(proof_type: str) -> dict:
    payloads = {
        "deployment": {
            "proof_type": "deployment",
            "proof_id": "deployment-proof-test",
            "created_at": "2026-07-02T00:00:00Z",
            "environment": "production-redacted",
            "deployment_provider": "managed-cloud-redacted",
            "app_url_redacted": "https://careeragent-redacted.example.invalid",
            "backend_health_passed": True,
            "readiness_passed": True,
            "migration_status": "up_to_date",
            "managed_database": True,
            "secret_manager_used": True,
            "kms_or_encryption_key_used": True,
            "tls_enabled": True,
            "rollback_plan_verified": True,
            "smoke_tests_passed": True,
            "evidence_refs": ["deployment-run-redacted"],
            "production_quality_candidate_signal": True,
            "limitations": [],
        },
        "backup_purge": {
            "proof_type": "backup_purge",
            "proof_id": "backup-purge-test",
            "created_at": "2026-07-02T00:00:00Z",
            "database_backup_verified": True,
            "restore_test_passed": True,
            "delete_all_test_passed": True,
            "backup_purge_verified": True,
            "legal_hold_behavior_verified": True,
            "restore_after_delete_blocked_or_redacted": True,
            "retention_policy_documented": True,
            "evidence_refs": ["backup-purge-run-redacted"],
            "production_quality_candidate_signal": True,
            "limitations": [],
        },
        "monitoring": {
            "proof_type": "monitoring",
            "proof_id": "monitoring-proof-test",
            "created_at": "2026-07-02T00:00:00Z",
            "logs_enabled": True,
            "metrics_enabled": True,
            "tracing_enabled": True,
            "error_reporting_enabled": True,
            "alert_rules_configured": True,
            "health_check_alert_verified": True,
            "incident_runbook_exists": True,
            "dashboard_refs": ["monitoring-dashboard-redacted"],
            "production_quality_candidate_signal": True,
            "limitations": [],
        },
        "security_review": {
            "proof_type": "security_review",
            "proof_id": "security-review-test",
            "created_at": "2026-07-02T00:00:00Z",
            "reviewer": "external-reviewer-redacted",
            "review_scope": ["auth", "privacy", "deployment", "dependencies"],
            "auth_session_review_passed": True,
            "privacy_review_passed": True,
            "dependency_scan_passed": True,
            "secret_scan_passed": True,
            "pii_redaction_review_passed": True,
            "rate_limit_review_passed": True,
            "vulnerability_findings": [],
            "critical_findings_count": 0,
            "high_findings_count": 0,
            "unresolved_findings_count": 0,
            "production_quality_candidate_signal": True,
            "limitations": [],
        },
    }
    return payloads[proof_type]


def _write_proofs(path: Path, proofs: list[dict]) -> None:
    for proof in proofs:
        path.joinpath(f"{proof['proof_type']}.json").write_text(
            json.dumps(proof),
            encoding="utf-8",
        )


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


def test_external_ops_schemas_and_templates_are_v35c_template_only():
    required_fields = {
        "deployment": {
            "environment",
            "deployment_provider",
            "app_url_redacted",
            "backend_health_passed",
            "readiness_passed",
            "migration_status",
            "managed_database",
            "secret_manager_used",
            "kms_or_encryption_key_used",
            "tls_enabled",
            "rollback_plan_verified",
            "smoke_tests_passed",
            "evidence_refs",
            "production_quality_candidate_signal",
            "limitations",
        },
        "backup_purge": {
            "database_backup_verified",
            "restore_test_passed",
            "delete_all_test_passed",
            "backup_purge_verified",
            "legal_hold_behavior_verified",
            "restore_after_delete_blocked_or_redacted",
            "retention_policy_documented",
            "evidence_refs",
            "production_quality_candidate_signal",
            "limitations",
        },
        "monitoring": {
            "logs_enabled",
            "metrics_enabled",
            "tracing_enabled",
            "error_reporting_enabled",
            "alert_rules_configured",
            "health_check_alert_verified",
            "incident_runbook_exists",
            "dashboard_refs",
            "production_quality_candidate_signal",
            "limitations",
        },
        "security_review": {
            "reviewer",
            "review_scope",
            "auth_session_review_passed",
            "privacy_review_passed",
            "dependency_scan_passed",
            "secret_scan_passed",
            "pii_redaction_review_passed",
            "rate_limit_review_passed",
            "vulnerability_findings",
            "critical_findings_count",
            "high_findings_count",
            "unresolved_findings_count",
            "production_quality_candidate_signal",
            "limitations",
        },
    }

    for proof_type, fields in required_fields.items():
        schema = _json(ROOT / "evidence" / "schemas" / f"{proof_type}_proof.schema.json")
        template = _json(ROOT / "evidence" / "templates" / f"{proof_type}_proof.template.json")

        assert set(schema["required"]) >= fields | {"proof_type", "proof_id", "created_at"}
        assert template["template_only"] is True
        assert template["production_quality_candidate_signal"] is False
        assert "template_only" in template["limitations"]


def test_human_review_input_template_has_required_columns():
    template = ROOT / "evidence" / "templates" / "human_review_input.template.csv"
    with template.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert import_human_review_proof.REQUIRED_FIELDS <= set(reader.fieldnames or [])
    batch_template = ROOT / "evidence" / "templates" / "human_review_batch.template.csv"
    with batch_template.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert import_human_review_batch.REQUIRED_ITEM_FIELDS <= set(reader.fieldnames or [])


def test_private_outputs_are_gitignored():
    result = subprocess.run(
        ["git", "check-ignore", "-q", "evidence/private_outputs/test.json"],
        cwd=ROOT,
        check=False,
    )
    assert result.returncode == 0


def test_external_ops_template_generator_dry_run_does_not_write(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/create_external_ops_proof_template.py",
            "--proof-type",
            "deployment",
            "--output-dir",
            str(tmp_path),
            "--timestamp",
            "20260702T000000Z",
            "--dry-run",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    proof = payload["deployment"]
    assert proof["template_only"] is True
    assert proof["production_quality_candidate_signal"] is False
    assert "template_only" in proof["limitations"]
    assert list(tmp_path.iterdir()) == []


def test_external_ops_template_generator_writes_to_requested_dir(tmp_path):
    create_external_ops_proof_template.write_ops_templates(
        ["monitoring"],
        output_dir=tmp_path,
        generated_at="20260702T000000Z",
    )

    output = tmp_path / "monitoring_proof.template.20260702T000000Z.json"
    assert output.exists()
    assert _json(output)["proof_type"] == "monitoring"


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


def test_external_provider_probe_prompts_request_exact_json_shapes():
    grounded_prompt = run_external_provider_proof.GROUNDED_ANSWER_PROBE_PROMPT
    judge_prompt = run_external_provider_proof.LLM_JUDGE_PROBE_PROMPT

    for token in [
        "Return JSON only",
        "No markdown",
        "answer",
        "citations",
        "grounded",
        "chunk_safe_1",
    ]:
        assert token in grounded_prompt
    for token in [
        "Return JSON only",
        "No markdown",
        "groundedness_score",
        "factuality_score",
        "hallucination_flag",
        "evidence_refs",
        "chunk_safe_1",
    ]:
        assert token in judge_prompt


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


def test_human_review_batch_schema_validation_pass_and_fail(tmp_path):
    input_path = tmp_path / "reviews.csv"
    _write_human_review_csv(
        input_path,
        [
            _human_review_row(1, reviewer="reviewer:external_a"),
            _human_review_row(2, reviewer="reviewer:external_b"),
        ],
    )

    batch = import_human_review_batch.build_human_review_batch(
        input_path,
        batch_id="human-review-schema-test",
        privacy_sanitized=True,
    )

    assert import_human_review_batch.validate_human_review_batch_payload(batch) == []
    broken = dict(batch)
    broken.pop("review_batch_id")
    assert "missing required field: review_batch_id" in (
        import_human_review_batch.validate_human_review_batch_payload(broken)
    )


def test_human_review_batch_csv_and_jsonl_dry_run(tmp_path):
    csv_path = tmp_path / "reviews.csv"
    jsonl_path = tmp_path / "reviews.jsonl"
    rows = [
        _human_review_row(1, reviewer="reviewer:external_a"),
        _human_review_row(2, reviewer="reviewer:external_b"),
    ]
    _write_human_review_csv(csv_path, rows)
    jsonl_path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    for input_path in [csv_path, jsonl_path]:
        output_path = tmp_path / f"{input_path.stem}.json"
        result = subprocess.run(
            [
                "python3",
                "scripts/import_human_review_batch.py",
                "--input",
                str(input_path),
                "--output",
                str(output_path),
                "--dry-run",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        assert payload["proof_type"] == "human_review"
        assert output_path.exists() is False


def test_merge_human_review_batches_preserves_two_reviewer_judgments(tmp_path):
    batch_a = _single_reviewer_human_review_batch("reviewer:external_a")
    batch_b = _single_reviewer_human_review_batch("reviewer:external_b")
    path_a = tmp_path / "reviewer_a.json"
    path_b = tmp_path / "reviewer_b.json"
    path_a.write_text(json.dumps(batch_a), encoding="utf-8")
    path_b.write_text(json.dumps(batch_b), encoding="utf-8")

    merged = merge_human_review_batches.merge_human_review_batches(
        [path_a, path_b],
        batch_id="human-review-merged-test",
    )

    assert merged["proof_type"] == "human_review"
    assert merged["reviewer_count"] == 2
    assert merged["sample_size"] == 30
    assert len(merged["review_items"]) == 60
    assert merged["agreement_metrics"]["comparable_item_count"] == 30
    assert merged["agreement_metrics"]["decision_agreement_rate"] == 1.0
    assert merged["summary"]["pass_rate"] == 1.0
    assert merged["production_quality_candidate_signal"] is True
    assert import_human_review_batch.validate_human_review_batch_payload(merged) == []


def test_merge_human_review_batches_rejects_same_reviewer_duplicate_item(tmp_path):
    batch_a = _single_reviewer_human_review_batch("reviewer:external_a")
    path_a = tmp_path / "reviewer_a.json"
    path_b = tmp_path / "reviewer_a_copy.json"
    path_a.write_text(json.dumps(batch_a), encoding="utf-8")
    path_b.write_text(json.dumps(batch_a), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate review"):
        merge_human_review_batches.merge_human_review_batches([path_a, path_b])


def test_merge_human_review_batches_dry_run_cli(tmp_path):
    path_a = tmp_path / "reviewer_a.json"
    path_b = tmp_path / "reviewer_b.json"
    path_a.write_text(
        json.dumps(_single_reviewer_human_review_batch("reviewer:external_a")),
        encoding="utf-8",
    )
    path_b.write_text(
        json.dumps(_single_reviewer_human_review_batch("reviewer:external_b")),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/merge_human_review_batches.py",
            "--input",
            str(path_a),
            "--input",
            str(path_b),
            "--output",
            str(tmp_path / "merged.json"),
            "--dry-run",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["reviewer_count"] == 2
    assert payload["agreement_metrics"]["comparable_item_count"] == 30
    assert (tmp_path / "merged.json").exists() is False


def test_human_review_batch_blocks_pii_and_raw_private_fields(tmp_path):
    input_path = tmp_path / "reviews.csv"
    row = _human_review_row(1)
    row["reviewer_comment"] = "contact reviewer@example.invalid"
    _write_human_review_csv(input_path, [row])

    try:
        import_human_review_batch.build_human_review_batch(input_path)
    except ValueError as exc:
        assert "obvious PII" in str(exc)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("PII row should be rejected")

    raw_path = tmp_path / "raw.csv"
    raw_row = _human_review_row(1)
    raw_row["raw_text"] = "raw resume text must never be imported"
    _write_human_review_csv(raw_path, [raw_row])
    try:
        import_human_review_batch.build_human_review_batch(raw_path)
    except ValueError as exc:
        assert "private field raw_text" in str(exc)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("raw private row should be rejected")


def test_human_review_summary_metrics_and_thresholds(tmp_path):
    input_path = tmp_path / "reviews.csv"
    rows = [
        _human_review_row(index, reviewer="reviewer:external_a" if index % 2 else "reviewer:external_b")
        for index in range(1, 31)
    ]
    _write_human_review_csv(input_path, rows)

    summary = summarize_human_review_evidence.build_human_review_summary(input_path)

    assert summary["total_items"] == 30
    assert summary["pass_count"] == 30
    assert summary["pass_rate"] == 1.0
    assert summary["hallucination_rate"] == 0.0
    assert summary["fabrication_rate"] == 0.0
    assert summary["privacy_risk_count"] == 0
    assert summary["adjudication_completion_rate"] == 1.0
    assert summary["production_quality_candidate_signal"] is True

    failing_summary = summarize_human_review_evidence.build_human_review_summary(
        input_path,
        min_sample_size=31,
    )
    assert failing_summary["production_quality_candidate_signal"] is False
    assert "insufficient_sample_size" in failing_summary["threshold_failures"]


def test_human_review_sample_pack_dry_run_generates_blank_reviewer_csv():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_human_review_sample_pack.py",
            "--sample-size",
            "30",
            "--seed",
            "7",
            "--dry-run",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    reader = csv.DictReader(io.StringIO(result.stdout))
    rows = list(reader)

    assert len(rows) == 30
    assert set(reader.fieldnames or []) == set(generate_human_review_sample_pack.CSV_FIELDS)
    assert {row["task_type"] for row in rows} == set(generate_human_review_sample_pack.TASK_MODULES)
    for row in rows:
        assert row["anonymized_input_ref"].startswith("anonymized_benchmark:")
        assert row["model_output_ref"].startswith("anonymized_benchmark:")
        assert row["task_type_label"]
        assert row["input_summary"]
        assert row["model_output_summary"]
        assert row["review_instruction"]
        _assert_readable_review_context(row)
        assert row["reviewer_id_hash"] == ""
        assert row["correctness_score"] == ""
        assert row["groundedness_score"] == ""
        assert row["safety_score"] == ""
        assert row["usefulness_score"] == ""
        assert row["decision"] == ""
        assert row["reviewer_comment"] == ""


def test_human_review_sample_pack_contains_no_obvious_pii():
    rows = generate_human_review_sample_pack.build_sample_pack_rows(sample_size=30, seed=11)
    rendered = generate_human_review_sample_pack.render_csv(rows)

    assert "raw_resume" not in rendered
    assert "resume_text" not in rendered
    assert "jd_text" not in rendered
    assert "interview_answer" not in rendered
    assert not any(pattern.search(rendered) for pattern in generate_human_review_sample_pack.PII_PATTERNS)


def test_human_review_sample_pack_summaries_are_task_specific_and_readable():
    rows = generate_human_review_sample_pack.build_sample_pack_rows(sample_size=30, seed=7)
    by_task = {row["task_type"]: row for row in rows}

    expected_keywords = {
        "jd_parse": ["Anonymized job title", "responsibilities", "required skills", "role_category"],
        "resume_parse": ["Anonymized candidate profile", "visible sections", "project keywords", "skills="],
        "match_score": ["Anonymized JD/resume pair", "candidate evidence areas", "Model/system match score"],
        "rag_answer": ["User question", "safe evidence/citation summary", "Model answer summary"],
        "project_rewrite": ["Original project summary", "target JD requirement summary", "Model rewrite summary"],
        "agent_workflow": ["User goal", "expected state", "Agent output summary"],
    }
    for task_type, keywords in expected_keywords.items():
        row = by_task[task_type]
        _assert_readable_review_context(row)
        combined = f"{row['input_summary']} {row['model_output_summary']}"
        for keyword in keywords:
            assert keyword in combined


def test_anonymized_parser_benchmark_signals_do_not_add_unsupported_bad_case_fields():
    jd_rows = _jsonl(ROOT / "evals" / "datasets" / "anonymized_benchmark" / "jd_parser_benchmark.jsonl")
    resume_rows = _jsonl(
        ROOT / "evals" / "datasets" / "anonymized_benchmark" / "resume_parser_benchmark.jsonl"
    )

    for row in jd_rows:
        expected = row["expected"]
        signals = row["signals"]
        assert set(signals["parsed_required_skills"]) <= set(expected["required_skills_should_include"])
        assert set(signals["parsed_preferred_skills"]) <= set(expected["preferred_skills_should_include"])
        assert set(signals["risk_flags"]) <= set(expected["risk_flags_should_include"])
    for row in resume_rows:
        expected = row["expected"]
        signals = row["signals"]
        assert set(signals["skills"]) <= set(expected["skills_should_include"])
        assert set(signals["projects"]) <= set(expected["projects_should_include"])
        assert set(signals["sections"]) <= set(expected["sections_should_include"])
        assert set(signals["risk_flags"]) <= set(expected["risk_flags_should_include"])


def test_human_review_sample_pack_summaries_support_bad_case_outputs():
    rows = generate_human_review_sample_pack.build_sample_pack_rows(sample_size=30, seed=35)
    by_item = {row["item_id"]: row for row in rows}

    jd_041 = by_item["hr_jd_parse_anon_jd_041"]
    assert "REST" not in jd_041["model_output_summary"]
    assert "Python" in jd_041["input_summary"]
    assert "FastAPI" in jd_041["input_summary"]
    assert "PostgreSQL" in jd_041["input_summary"]

    jd_048 = by_item["hr_jd_parse_anon_jd_048"]
    assert "Mobile Graduate Engineer" in jd_048["input_summary"]
    assert "React Native" in jd_048["input_summary"]
    assert "backend" not in jd_048["input_summary"].lower()

    for item_id in [
        "hr_resume_parse_anon_resume_003",
        "hr_resume_parse_anon_resume_010",
        "hr_resume_parse_anon_resume_012",
        "hr_resume_parse_anon_resume_023",
        "hr_resume_parse_anon_resume_026",
    ]:
        row = by_item[item_id]
        assert "Git" not in row["model_output_summary"]
        assert "Evidence Portfolio" not in row["model_output_summary"]
        assert "experience section expected=True" not in row["model_output_summary"]
        for field in ["input_summary", "model_output_summary", "review_instruction"]:
            assert row[field]


def test_human_review_sample_pack_default_outputs_are_private_outputs():
    assert generate_human_review_sample_pack.default_output_for_format("csv").startswith(
        "evidence/private_outputs/human_review_sample_pack."
    )
    assert generate_human_review_sample_pack.default_output_for_format("csv").endswith(".csv")
    assert generate_human_review_sample_pack.default_output_for_format("xlsx").startswith(
        "evidence/private_outputs/human_review_fillable_simple_"
    )
    assert generate_human_review_sample_pack.default_output_for_format("xlsx").endswith(".xlsx")


def test_human_review_sample_pack_generates_simple_fillable_xlsx(tmp_path):
    output = tmp_path / "reviewer-pack.xlsx"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_human_review_sample_pack.py",
            "--sample-size",
            "30",
            "--seed",
            "7",
            "--format",
            "xlsx",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == str(output)
    workbook_xml = _xlsx_workbook_xml(output)
    for sheet_name in ["审核卡片", "填写说明"]:
        assert f'name="{sheet_name}"' in workbook_xml
    assert 'name="填写表"' not in workbook_xml
    assert 'name="导入字段_不要改"' not in workbook_xml
    assert 'name="选项"' not in workbook_xml
    assert "<autoFilter" not in workbook_xml
    assert 'state="hidden"' not in workbook_xml
    _assert_xlsx_has_no_complex_ooxml(output)
    generate_human_review_sample_pack.assert_xlsx_compatibility_smoke(output)

    for field in [
        "dataset_name",
        "sampling_method",
        "reviewer_role",
        "privacy_sanitized",
        "anonymized_input_ref",
        "model_output_ref",
    ]:
        assert field not in workbook_xml

    cards = _xlsx_card_rows(output)
    assert len(cards) == 30
    assert {card["task_type_label"] for card in cards} == set(
        generate_human_review_sample_pack.TASK_TYPE_LABELS.values()
    )
    for card in cards:
        assert card["item_id"].startswith("hr_")
        assert card["task_type_label"]
        assert card["input_summary"]
        assert card["model_output_summary"]
        assert card["review_instruction"]
        assert card["correctness_score"] == ""
        assert card["decision"] == ""
        _assert_readable_review_context(card)
    rendered = "\n".join(",".join(card.values()) for card in cards)
    assert not any(pattern.search(rendered) for pattern in generate_human_review_sample_pack.PII_PATTERNS)


def test_human_review_sample_pack_openpyxl_smoke_loads_card_workbook(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    output = tmp_path / "reviewer-pack.xlsx"
    rows = generate_human_review_sample_pack.build_sample_pack_rows(sample_size=30, seed=7)

    generate_human_review_sample_pack.render_xlsx(rows, output)

    workbook = openpyxl.load_workbook(output)
    assert workbook.sheetnames == ["审核卡片", "填写说明"]
    assert workbook["审核卡片"]["A1"].value == "样本 1 / 30"
    assert workbook["审核卡片"]["A2"].value == "item_id"
    workbook.close()


def test_human_review_card_xlsx_import_reads_filled_values(tmp_path):
    output = tmp_path / "completed-review.xlsx"
    rows = generate_human_review_sample_pack.build_sample_pack_rows(sample_size=30, seed=7)
    for row in rows:
        row["reviewer_id_hash"] = "reviewer:external_a"
        row["correctness_score"] = "0.8"
        row["groundedness_score"] = "0.9"
        row["safety_score"] = "1.0"
        row["usefulness_score"] = "0.95"
        row["privacy_risk_flag"] = "false"
        row["hallucination_flag"] = "false"
        row["fabrication_flag"] = "false"
        row["reviewer_comment"] = "synthetic completed workbook row"
        row["decision"] = "pass"
        row["requires_adjudication"] = "false"

    generate_human_review_sample_pack.render_xlsx(rows, output)

    loaded_rows = import_human_review_batch.load_review_rows(output)
    assert len(loaded_rows) == 30
    assert loaded_rows[0]["correctness_score"] == "0.8"
    assert loaded_rows[0]["groundedness_score"] == "0.9"
    assert loaded_rows[0]["decision"] == "pass"
    assert loaded_rows[0]["privacy_risk_flag"] == "false"
    assert loaded_rows[0]["reviewer_id_hash"] == "reviewer:external_a"

    batch = import_human_review_batch.build_human_review_batch(output)
    assert batch["sample_size"] == 30
    assert batch["review_items"][0]["correctness_score"] == 0.8
    assert batch["review_items"][0]["groundedness_score"] == 0.9
    assert batch["review_items"][0]["privacy_risk_flag"] is False


def test_human_review_card_xlsx_import_rejects_blank_scores_not_cached_zero(tmp_path):
    output = tmp_path / "blank-review.xlsx"
    rows = generate_human_review_sample_pack.build_sample_pack_rows(sample_size=30, seed=7)
    for row in rows:
        row["reviewer_id_hash"] = "reviewer:external_a"
        row["privacy_risk_flag"] = "false"
        row["hallucination_flag"] = "false"
        row["fabrication_flag"] = "false"
        row["decision"] = "pass"
        row["requires_adjudication"] = "false"

    generate_human_review_sample_pack.render_xlsx(rows, output)

    with pytest.raises(ValueError, match="correctness_score must be a number"):
        import_human_review_batch.build_human_review_batch(output)


def test_human_review_card_xlsx_import_rejects_blank_flags(tmp_path):
    output = tmp_path / "blank-flag-review.xlsx"
    rows = generate_human_review_sample_pack.build_sample_pack_rows(sample_size=30, seed=7)
    for row in rows:
        row["reviewer_id_hash"] = "reviewer:external_a"
        row["correctness_score"] = "1.0"
        row["groundedness_score"] = "1.0"
        row["safety_score"] = "1.0"
        row["usefulness_score"] = "1.0"
        row["privacy_risk_flag"] = ""
        row["hallucination_flag"] = "false"
        row["fabrication_flag"] = "false"
        row["decision"] = "pass"
        row["requires_adjudication"] = "false"

    generate_human_review_sample_pack.render_xlsx(rows, output)

    with pytest.raises(ValueError, match="privacy_risk_flag must be true or false"):
        import_human_review_batch.build_human_review_batch(output)


def test_human_review_card_xlsx_import_normalizes_bool_and_decision_values(tmp_path):
    output = tmp_path / "localized-review.xlsx"
    rows = generate_human_review_sample_pack.build_sample_pack_rows(sample_size=30, seed=7)
    for row in rows:
        row["reviewer_id_hash"] = "reviewer:external_a"
        row["correctness_score"] = "1.0"
        row["groundedness_score"] = "1.0"
        row["safety_score"] = "1.0"
        row["usefulness_score"] = "1.0"
        row["privacy_risk_flag"] = "否"
        row["hallucination_flag"] = "FALSE"
        row["fabrication_flag"] = "是"
        row["decision"] = "PASS"
        row["requires_adjudication"] = "TRUE"
        row["adjudication_decision"] = "通过"

    generate_human_review_sample_pack.render_xlsx(rows, output)

    item = import_human_review_batch.build_human_review_batch(output)["review_items"][0]
    assert item["privacy_risk_flag"] is False
    assert item["hallucination_flag"] is False
    assert item["fabrication_flag"] is True
    assert item["decision"] == "pass"
    assert item["requires_adjudication"] is True
    assert item["adjudication_decision"] == "pass"


def test_human_review_sample_pack_template_is_not_real_evidence(tmp_path):
    template = ROOT / "evidence" / "templates" / "human_review_sample_pack.template.csv"
    reader = csv.DictReader(io.StringIO(template.read_text(encoding="utf-8")))
    rows = list(reader)

    assert rows
    assert {row["dataset_name"] for row in rows} == {"template_only_dataset"}
    (tmp_path / template.name).write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    summary = validate_external_evidence_package.validate_evidence_package(tmp_path)
    assert summary["artifact_count"] == 0
    assert summary["human_review_status"] == "missing_human_review"
    assert summary["production_ready_candidate_possible"] is False


def test_evidence_validator_blocks_missing_external_proofs(tmp_path):
    summary = validate_external_evidence_package.validate_evidence_package(tmp_path)

    assert summary["production_ready_candidate_possible"] is False
    assert summary["human_review_status"] == "missing_human_review"
    assert "provider" in summary["missing_external_proofs"]
    assert "security_review" in summary["certified_blockers"][-1]


def test_evidence_validator_rejects_template_only_human_review(tmp_path):
    template = _json(ROOT / "evidence" / "templates" / "human_review_batch.template.json")
    (tmp_path / "human_review.json").write_text(json.dumps(template), encoding="utf-8")

    summary = validate_external_evidence_package.validate_evidence_package(tmp_path)

    assert summary["human_review_status"] == "template_only"
    assert summary["production_ready_candidate_possible"] is False
    assert "human review proof status: template_only" in summary["candidate_blockers"]


def test_evidence_validator_reports_human_review_threshold_statuses(tmp_path):
    insufficient = _human_review_batch_payload(sample_size=2)
    (tmp_path / "human_review.json").write_text(json.dumps(insufficient), encoding="utf-8")

    summary = validate_external_evidence_package.validate_evidence_package(tmp_path)

    assert summary["human_review_status"] == "insufficient_sample_size"

    failing = _human_review_batch_payload(sample_size=30)
    failing["summary"]["pass_rate"] = 0.5
    failing["production_quality_candidate_signal"] = False
    (tmp_path / "human_review.json").write_text(json.dumps(failing), encoding="utf-8")

    summary = validate_external_evidence_package.validate_evidence_package(tmp_path)

    assert summary["human_review_status"] == "thresholds_failed"


def test_evidence_validator_ignores_summary_and_validator_outputs(tmp_path):
    (tmp_path / "human_review_summary.json").write_text(
        json.dumps(
            {
                "summary_type": "human_review_summary",
                "source_review_batch_id": "human-review-test",
                "total_items": 30,
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "external_evidence_validation.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-02T00:00:00Z",
                "artifact_count": 1,
                "human_review_status": "thresholds_failed",
            }
        ),
        encoding="utf-8",
    )

    summary = validate_external_evidence_package.validate_evidence_package(tmp_path)

    assert summary["schema_validation_passed"] is True
    assert summary["artifact_count"] == 0
    assert summary["valid_artifact_count"] == 0
    assert summary["human_review_status"] == "missing_human_review"
    assert summary["invalid_artifacts"] == []
    assert {item["path"] for item in summary["ignored_artifacts"]} == {
        "human_review_summary.json",
        "external_evidence_validation.json",
    }


def test_evidence_validator_keeps_single_reviewer_human_review_blocked(tmp_path):
    (tmp_path / "human_review.json").write_text(
        json.dumps(_single_reviewer_human_review_batch("reviewer:external_a")),
        encoding="utf-8",
    )

    summary = validate_external_evidence_package.validate_evidence_package(tmp_path)

    assert summary["human_review_status"] == "thresholds_failed"
    assert summary["production_ready_candidate_possible"] is False
    assert "human review proof status: thresholds_failed" in summary["candidate_blockers"]


def test_evidence_validator_accepts_two_reviewer_human_review_status(tmp_path):
    path_a = tmp_path / "reviewer_a.json"
    path_b = tmp_path / "reviewer_b.json"
    path_a.write_text(
        json.dumps(_single_reviewer_human_review_batch("reviewer:external_a")),
        encoding="utf-8",
    )
    path_b.write_text(
        json.dumps(_single_reviewer_human_review_batch("reviewer:external_b")),
        encoding="utf-8",
    )
    merged = merge_human_review_batches.merge_human_review_batches([path_a, path_b])
    (tmp_path / "human_review.json").write_text(json.dumps(merged), encoding="utf-8")

    summary = validate_external_evidence_package.validate_evidence_package(tmp_path)

    assert summary["human_review_status"] == "human_review_candidate_passed"
    assert "human review proof status" not in "\n".join(summary["candidate_blockers"])


def test_evidence_validator_reports_external_ops_statuses(tmp_path):
    summary = validate_external_evidence_package.validate_evidence_package(tmp_path)
    assert summary["deployment_status"] == "missing_deployment"
    assert summary["backup_purge_status"] == "missing_backup_purge"
    assert summary["monitoring_status"] == "missing_monitoring"
    assert summary["security_review_status"] == "missing_security_review"

    for proof_type in ["deployment", "backup_purge", "monitoring", "security_review"]:
        template = _json(ROOT / "evidence" / "templates" / f"{proof_type}_proof.template.json")
        (tmp_path / f"{proof_type}.json").write_text(json.dumps(template), encoding="utf-8")

    summary = validate_external_evidence_package.validate_evidence_package(tmp_path)
    assert summary["deployment_status"] == "deployment_template_only"
    assert summary["backup_purge_status"] == "backup_purge_template_only"
    assert summary["monitoring_status"] == "monitoring_template_only"
    assert summary["security_review_status"] == "security_review_template_only"
    assert summary["production_ready_candidate_possible"] is False


def test_evidence_validator_reports_external_ops_threshold_failures(tmp_path):
    for proof_type in ["deployment", "backup_purge", "monitoring", "security_review"]:
        proof = _ops_proof_payload(proof_type)
        proof["production_quality_candidate_signal"] = False
        (tmp_path / f"{proof_type}.json").write_text(json.dumps(proof), encoding="utf-8")

    summary = validate_external_evidence_package.validate_evidence_package(tmp_path)

    assert summary["deployment_status"] == "deployment_thresholds_failed"
    assert summary["backup_purge_status"] == "backup_purge_thresholds_failed"
    assert summary["monitoring_status"] == "monitoring_thresholds_failed"
    assert summary["security_review_status"] == "security_review_thresholds_failed"
    assert "deployment proof status: deployment_thresholds_failed" in summary["candidate_blockers"]


def test_evidence_validator_accepts_external_ops_candidate_statuses(tmp_path):
    for proof_type in ["deployment", "backup_purge", "monitoring", "security_review"]:
        (tmp_path / f"{proof_type}.json").write_text(
            json.dumps(_ops_proof_payload(proof_type)),
            encoding="utf-8",
        )

    summary = validate_external_evidence_package.validate_evidence_package(tmp_path)

    assert summary["deployment_status"] == "deployment_candidate_passed"
    assert summary["backup_purge_status"] == "backup_purge_candidate_passed"
    assert summary["monitoring_status"] == "monitoring_candidate_passed"
    assert summary["security_review_status"] == "security_review_candidate_passed"
    assert "deployment proof status" not in "\n".join(summary["candidate_blockers"])


def test_evidence_validator_requires_security_review_for_candidate_and_certified(tmp_path):
    proofs = [_provider_proof_payload(), _human_review_batch_payload()]
    proofs.extend(
        _ops_proof_payload(proof_type)
        for proof_type in ["deployment", "backup_purge", "monitoring"]
    )
    _write_proofs(tmp_path, proofs)

    summary = validate_external_evidence_package.validate_evidence_package(tmp_path)

    assert summary["production_ready_candidate_possible"] is False
    assert summary["production_readiness_certified_possible"] is False
    assert "missing external proof: security_review" in summary["candidate_blockers"]
    assert "missing external proof: security_review" in summary["certified_blockers"]


def test_evidence_validator_accepts_complete_redacted_package(tmp_path):
    proofs = [_provider_proof_payload(), _human_review_batch_payload()]
    proofs.extend(
        _ops_proof_payload(proof_type)
        for proof_type in ["deployment", "backup_purge", "monitoring", "security_review"]
    )
    _write_proofs(tmp_path, proofs)

    summary = validate_external_evidence_package.validate_evidence_package(tmp_path)

    assert summary["schema_validation_passed"] is True
    assert summary["secret_leak_check_passed"] is True
    assert summary["human_review_status"] == "human_review_candidate_passed"
    assert summary["deployment_status"] == "deployment_candidate_passed"
    assert summary["backup_purge_status"] == "backup_purge_candidate_passed"
    assert summary["monitoring_status"] == "monitoring_candidate_passed"
    assert summary["security_review_status"] == "security_review_candidate_passed"
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
    assert "LLM_TIMEOUT_SECONDS=30" in docs
    assert "EMBEDDING_DIMENSION=1536" in docs


def test_final_readiness_gate_requires_external_evidence_package():
    script = (ROOT / "scripts" / "run_final_readiness_gates.sh").read_text(encoding="utf-8")

    assert "scripts/validate_external_evidence_package.py" in script
    assert "production_ready_candidate_possible" in script
    assert "human_review_status" in script


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
