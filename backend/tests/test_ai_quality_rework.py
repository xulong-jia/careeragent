from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

from app.evaluation import ai_quality
from scripts import run_evals
from scripts.validate_ai_providers import build_provider_proof


class _FakeProviderHandler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("content-length", "0"))
        self.rfile.read(length)
        if self.path.endswith("/chat/completions"):
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
        else:
            body = {"data": [{"embedding": [0.1, 0.2, 0.3, 0.4]}]}
        payload = json.dumps(body).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args):
        return


def test_provider_validation_supports_offline_without_secret(monkeypatch):
    for key in [
        "LLM_API_BASE_URL",
        "LLM_API_KEY",
        "LLM_MODEL",
        "EMBEDDING_API_BASE_URL",
        "EMBEDDING_API_KEY",
        "EMBEDDING_MODEL",
    ]:
        monkeypatch.delenv(key, raising=False)

    proof = build_provider_proof()

    assert proof["status"] == "pass"
    assert proof["provider_mode"] == "offline"
    assert proof["secrets_masked"] is True


def test_provider_validation_accepts_fake_openai_compatible_server(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), _FakeProviderHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        monkeypatch.setenv("LLM_API_BASE_URL", base_url)
        monkeypatch.setenv("LLM_API_KEY", "test-provider-key")
        monkeypatch.setenv("LLM_MODEL", "fake-chat")
        monkeypatch.setenv("EMBEDDING_API_BASE_URL", base_url)
        monkeypatch.setenv("EMBEDDING_API_KEY", "test-embedding-key")
        monkeypatch.setenv("EMBEDDING_MODEL", "fake-embedding")
        monkeypatch.setenv("EMBEDDING_DIMENSION", "4")

        proof = build_provider_proof(require_provider=True)

        assert proof["status"] == "pass"
        assert proof["provider_mode"] == "provider_verified"
        assert proof["checks"]["llm"]["schema_validated"] is True
        assert proof["checks"]["embedding"]["dimension"] == 4
        assert "test-provider-key" not in json.dumps(proof)
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_formal_human_review_and_llm_judge_metrics():
    reviews = ai_quality.parse_formal_human_review_records(
        [
            {
                "reviewer_id": "reviewer_a",
                "review_role": "career_reviewer",
                "review_timestamp": "2026-07-01T00:00:00Z",
                "rubric_version": "human-review-v3.4",
                "module": "match",
                "case_id": "case_1",
                "human_score": 84,
                "human_label": "accept",
                "confidence": 0.9,
                "accepted_output": True,
                "rejected_output": False,
                "correction_note": "",
                "privacy_review_passed": True,
            },
            {
                "reviewer_id": "reviewer_b",
                "review_role": "career_reviewer",
                "review_timestamp": "2026-07-01T00:00:00Z",
                "rubric_version": "human-review-v3.4",
                "module": "match",
                "case_id": "case_1",
                "human_score": 82,
                "human_label": "accept",
                "confidence": 0.8,
                "accepted_output": True,
                "rejected_output": False,
                "correction_note": "",
                "privacy_review_passed": True,
            },
        ]
    )
    judges = ai_quality.parse_llm_judge_records(
        [
            {
                "case_id": "case_1",
                "module": "match",
                "rubric_version": "llm-judge-v3.4",
                "groundedness_score": 0.9,
                "factuality_score": 0.9,
                "completeness_score": 0.8,
                "hallucination_flag": False,
                "evidence_alignment_score": 0.9,
                "evidence_refs": ["case_1:evidence"],
            }
        ]
    )

    assert ai_quality.compute_two_reviewer_agreement(reviews)["agreement_rate"] == 1.0
    assert ai_quality.compute_llm_judge_summary(judges)["hallucination_rate"] == 0.0


def test_anonymized_benchmark_runner_writes_privacy_safe_outputs(tmp_path):
    status = run_evals.run("anonymized_benchmark", None, tmp_path)

    metrics = json.loads((tmp_path / "metrics.json").read_text())
    actual_outputs = (tmp_path / "actual_outputs.json").read_text()
    assert status == 0
    assert metrics["total_count"] >= 150
    assert metrics["pass_rate"] == 1.0
    assert metrics["human_review"]["agreement_rate"] >= 0.8
    assert metrics["llm_judge"]["hallucination_rate"] == 0.0
    assert "@" not in actual_outputs
    assert "0400" not in actual_outputs
