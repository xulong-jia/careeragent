#!/usr/bin/env python3
"""Build a redacted external provider proof shell for v3.5 evidence review."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any
import uuid

try:
    from .validate_ai_providers import build_provider_proof
except ImportError:  # pragma: no cover - direct script execution path
    from validate_ai_providers import build_provider_proof


DEFAULT_OUTPUT = "evidence/private_outputs/provider_proof.{timestamp}.json"
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]+"),
    re.compile(r"ghp_[A-Za-z0-9_]+"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(authorization|api[_-]?key|token|secret)[\"'=:\s]+[A-Za-z0-9_./+=-]{12,}"),
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact_value(value: str) -> str:
    if not value:
        return ""
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"[set length={len(value)} sha256:{digest}]"


def _secret_leak_check(payload: dict[str, Any]) -> bool:
    rendered = json.dumps(payload, sort_keys=True)
    return not any(pattern.search(rendered) for pattern in SECRET_PATTERNS)


def _output_path(path: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path(path.format(timestamp=timestamp))


def build_external_provider_proof(
    *,
    dry_run: bool,
    provider: str,
    embedding_model: str,
    llm_model: str,
    timeout_retry_validation_passed: bool = False,
    rag_grounded_answer_sample_passed: bool = False,
    llm_judge_sample_passed: bool = False,
) -> dict[str, Any]:
    base_url = os.getenv("LLM_API_BASE_URL") or os.getenv("EMBEDDING_API_BASE_URL", "")
    proof_id = f"provider-proof-{uuid.uuid4().hex[:12]}"
    limitations: list[str] = []

    if dry_run:
        provider_mode = "not_verified"
        embedding_passed = False
        llm_passed = False
        schema_passed = False
        limitations.extend(
            [
                "Dry-run only; no external provider call was made.",
                "This artifact is a shape check and cannot support production readiness.",
            ]
        )
        raw_provider_proof: dict[str, Any] = {
            "status": "dry_run",
            "provider_mode": "not_verified",
            "checks": {},
        }
    else:
        overrides = {
            "EMBEDDING_MODEL": embedding_model,
            "LLM_MODEL": llm_model,
        }
        original_env = {key: os.environ.get(key) for key in overrides}
        for key, value in overrides.items():
            if value:
                os.environ[key] = value
        try:
            raw_provider_proof = build_provider_proof(require_provider=True)
        finally:
            for key, original in original_env.items():
                if original is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original
        raw_mode = raw_provider_proof.get("provider_mode")
        provider_mode = "provider_verified" if raw_mode == "provider_verified" else "failed"
        checks = raw_provider_proof.get("checks", {})
        embedding = checks.get("embedding", {})
        llm = checks.get("llm", {})
        embedding_passed = embedding.get("status") == "pass"
        llm_passed = llm.get("status") == "pass"
        schema_passed = bool(llm.get("schema_validated")) and llm_passed
        if provider_mode != "provider_verified":
            limitations.append("External provider validation did not pass.")
        if not timeout_retry_validation_passed:
            limitations.append("Operator has not attached timeout/retry validation evidence.")
        if not rag_grounded_answer_sample_passed:
            limitations.append("Operator has not attached grounded RAG answer sample evidence.")
        if not llm_judge_sample_passed:
            limitations.append("Operator has not attached LLM judge sample evidence.")

    payload: dict[str, Any] = {
        "proof_type": "provider",
        "proof_id": proof_id,
        "created_at": _utc_now(),
        "provider": provider,
        "provider_mode": provider_mode,
        "base_url_redacted": _redact_value(base_url),
        "embedding_model": embedding_model or os.getenv("EMBEDDING_MODEL", ""),
        "llm_model": llm_model or os.getenv("LLM_MODEL", ""),
        "embedding_validation_passed": embedding_passed,
        "llm_validation_passed": llm_passed,
        "timeout_retry_validation": bool(timeout_retry_validation_passed and not dry_run),
        "schema_validation_passed": schema_passed,
        "rag_grounded_answer_sample_passed": bool(
            rag_grounded_answer_sample_passed and not dry_run
        ),
        "llm_judge_sample_passed": bool(llm_judge_sample_passed and not dry_run),
        "secret_leak_check_passed": True,
        "production_quality_candidate_signal": False,
        "limitations": limitations,
        "source_provider_probe": raw_provider_proof,
    }
    payload["secret_leak_check_passed"] = _secret_leak_check(payload)
    payload["production_quality_candidate_signal"] = all(
        [
            payload["provider_mode"] == "provider_verified",
            payload["embedding_validation_passed"],
            payload["llm_validation_passed"],
            payload["timeout_retry_validation"],
            payload["schema_validation_passed"],
            payload["rag_grounded_answer_sample_passed"],
            payload["llm_judge_sample_passed"],
            payload["secret_leak_check_passed"],
        ]
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--provider", default="openai_compatible")
    parser.add_argument("--embedding-model", default=os.getenv("EMBEDDING_MODEL", ""))
    parser.add_argument("--llm-model", default=os.getenv("LLM_MODEL", ""))
    parser.add_argument(
        "--timeout-retry-validation-passed",
        action="store_true",
        help="Set only after external timeout/retry evidence has been reviewed.",
    )
    parser.add_argument(
        "--rag-grounded-answer-sample-passed",
        action="store_true",
        help="Set only after grounded RAG sample evidence has been reviewed.",
    )
    parser.add_argument(
        "--llm-judge-sample-passed",
        action="store_true",
        help="Set only after LLM judge sample evidence has been reviewed.",
    )
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    proof = build_external_provider_proof(
        dry_run=args.dry_run,
        provider=args.provider,
        embedding_model=args.embedding_model,
        llm_model=args.llm_model,
        timeout_retry_validation_passed=args.timeout_retry_validation_passed,
        rag_grounded_answer_sample_passed=args.rag_grounded_answer_sample_passed,
        llm_judge_sample_passed=args.llm_judge_sample_passed,
    )
    output = _output_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(str(output))
    return 0 if proof["secret_leak_check_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
