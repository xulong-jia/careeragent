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
import sys
from typing import Any
import uuid

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

try:
    from .check_provider_proof_readiness import build_readiness_report
except ImportError:  # pragma: no cover - direct script execution path
    from check_provider_proof_readiness import build_readiness_report


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


def _redact_message(message: str) -> str:
    redacted = message
    for name in ("LLM_API_KEY", "EMBEDDING_API_KEY"):
        secret = os.getenv(name, "").strip()
        if secret:
            redacted = redacted.replace(secret, "[redacted]")
    redacted = re.sub(r"sk-[A-Za-z0-9_-]{8,}", "[redacted]", redacted)
    redacted = re.sub(
        r"(?i)(authorization:\s*bearer\s+)[^\s,;]+",
        r"\1[redacted]",
        redacted,
    )
    return redacted


def _safe_bool_probe(name: str, probe) -> tuple[bool, dict[str, str] | None]:
    try:
        return bool(probe()), None
    except Exception as exc:  # pragma: no cover - exercised by provider failures
        return False, {
            "probe": name,
            "error_type": type(exc).__name__,
            "message": _redact_message(str(exc)),
        }


def _is_fake_base_url(value: str) -> bool:
    return "://127." in value or "://localhost" in value or "://0.0.0.0" in value


def _env_value(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def _timeout_retry_validation() -> bool:
    try:
        return float(os.getenv("LLM_TIMEOUT_SECONDS", "10")) > 0
    except ValueError:
        return False


def _output_path(path: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path(path.format(timestamp=timestamp))


def _build_provider_proof(*, require_provider: bool) -> dict[str, Any]:
    try:
        from .validate_ai_providers import build_provider_proof
    except ImportError:  # pragma: no cover - direct script execution path
        from validate_ai_providers import build_provider_proof

    return build_provider_proof(require_provider=require_provider)


def _validate_grounded_answer() -> bool:
    from pydantic import BaseModel

    from app.ai.llm_provider import OpenAICompatibleLLMProvider

    class GroundedAnswerProbe(BaseModel):
        answer: str
        citations: list[str]
        grounded: bool

    provider = OpenAICompatibleLLMProvider(
        api_base_url=_env_value("LLM_API_BASE_URL", "LLM_BASE_URL"),
        api_key=_env_value("LLM_API_KEY"),
        model=_env_value("LLM_MODEL"),
        timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "10")),
    )
    output = provider.generate_structured(
        prompt=(
            "Use only this safe evidence: chunk_id=chunk_safe_1 says CareerAgent "
            "requires redacted provider proof. Return JSON with answer, citations "
            "containing chunk_safe_1, and grounded=true."
        ),
        schema=GroundedAnswerProbe,
        max_output_length=2000,
    )
    return output.grounded is True and "chunk_safe_1" in output.citations


def _validate_llm_judge() -> bool:
    from pydantic import BaseModel

    from app.ai.llm_provider import OpenAICompatibleLLMProvider

    class LLMJudgeProbe(BaseModel):
        groundedness_score: float
        factuality_score: float
        hallucination_flag: bool
        evidence_refs: list[str]

    provider = OpenAICompatibleLLMProvider(
        api_base_url=_env_value("LLM_API_BASE_URL", "LLM_BASE_URL"),
        api_key=_env_value("LLM_API_KEY"),
        model=_env_value("LLM_MODEL"),
        timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "10")),
    )
    output = provider.generate_structured(
        prompt=(
            "Return advisory judge JSON for a safe synthetic answer. Include "
            "groundedness_score=1.0, factuality_score=1.0, hallucination_flag=false, "
            "and evidence_refs containing chunk_safe_1."
        ),
        schema=LLMJudgeProbe,
        max_output_length=2000,
    )
    return (
        0 <= output.groundedness_score <= 1
        and 0 <= output.factuality_score <= 1
        and output.hallucination_flag is False
        and bool(output.evidence_refs)
    )


def _with_provider_env(
    *,
    llm_base_url: str,
    llm_model: str,
    embedding_base_url: str,
    embedding_model: str,
) -> dict[str, str | None]:
    overrides = {
        "LLM_API_BASE_URL": llm_base_url,
        "LLM_MODEL": llm_model,
        "EMBEDDING_API_BASE_URL": embedding_base_url,
        "EMBEDDING_MODEL": embedding_model,
    }
    original_env = {key: os.environ.get(key) for key in overrides}
    for key, value in overrides.items():
        if value:
            os.environ[key] = value
    return original_env


def _restore_env(original_env: dict[str, str | None]) -> None:
    for key, original in original_env.items():
        if original is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original


def build_external_provider_proof(
    *,
    dry_run: bool,
    provider: str,
    llm_base_url: str = "",
    embedding_base_url: str = "",
    embedding_model: str,
    llm_model: str,
    force_fake: bool = False,
) -> dict[str, Any]:
    resolved_llm_base_url = llm_base_url or _env_value("LLM_BASE_URL", "LLM_API_BASE_URL")
    resolved_embedding_base_url = embedding_base_url or _env_value(
        "EMBEDDING_BASE_URL",
        "EMBEDDING_API_BASE_URL",
    )
    resolved_llm_model = llm_model or _env_value("LLM_MODEL")
    resolved_embedding_model = embedding_model or _env_value("EMBEDDING_MODEL")
    proof_id = f"provider-proof-{uuid.uuid4().hex[:12]}"
    limitations: list[str] = []

    if dry_run:
        provider_mode = "dry_run"
        embedding_passed = False
        llm_passed = False
        schema_passed = False
        rag_passed = False
        judge_passed = False
        timeout_retry_passed = False
        probe_errors: list[dict[str, str]] = []
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
        original_env = _with_provider_env(
            llm_base_url=resolved_llm_base_url,
            llm_model=resolved_llm_model,
            embedding_base_url=resolved_embedding_base_url,
            embedding_model=resolved_embedding_model,
        )
        try:
            raw_provider_proof = _build_provider_proof(require_provider=True)
            checks = raw_provider_proof.get("checks", {})
            embedding = checks.get("embedding", {})
            llm = checks.get("llm", {})
            embedding_passed = embedding.get("status") == "pass" and bool(
                embedding.get("vector_nonzero")
            )
            llm_passed = llm.get("status") == "pass"
            schema_passed = bool(llm.get("schema_validated")) and llm_passed
            probe_errors = []
            if schema_passed:
                rag_passed, rag_error = _safe_bool_probe(
                    "rag_grounded_answer",
                    _validate_grounded_answer,
                )
                judge_passed, judge_error = _safe_bool_probe("llm_judge", _validate_llm_judge)
                probe_errors.extend(error for error in [rag_error, judge_error] if error)
            else:
                rag_passed = False
                judge_passed = False
            timeout_retry_passed = _timeout_retry_validation()
        finally:
            _restore_env(original_env)
        fake_url = force_fake or _is_fake_base_url(resolved_llm_base_url) or _is_fake_base_url(
            resolved_embedding_base_url
        )
        all_external_checks_passed = all(
            [embedding_passed, llm_passed, schema_passed, rag_passed, judge_passed]
        )
        if all_external_checks_passed and fake_url:
            provider_mode = "fake"
        elif all_external_checks_passed:
            provider_mode = "external_verified"
        else:
            provider_mode = "not_verified"
        if provider_mode != "external_verified":
            limitations.append("External provider validation did not pass.")
        if provider_mode == "fake":
            limitations.append("Provider endpoint is localhost; fake proof is test-only.")
        if not timeout_retry_passed:
            limitations.append("Timeout/retry configuration is invalid.")
        if not rag_passed:
            limitations.append("Grounded RAG answer probe did not pass.")
        if not judge_passed:
            limitations.append("LLM judge advisory probe did not pass.")

    payload: dict[str, Any] = {
        "proof_type": "provider",
        "proof_id": proof_id,
        "created_at": _utc_now(),
        "provider": provider,
        "provider_mode": provider_mode,
        "llm_provider": provider,
        "embedding_provider": provider,
        "base_url_redacted": {
            "llm": _redact_value(resolved_llm_base_url),
            "embedding": _redact_value(resolved_embedding_base_url),
        },
        "embedding_model": resolved_embedding_model,
        "llm_model": resolved_llm_model,
        "embedding_validation_passed": embedding_passed,
        "llm_validation_passed": llm_passed,
        "timeout_retry_validation": timeout_retry_passed,
        "schema_validation_passed": schema_passed,
        "rag_grounded_answer_sample_passed": rag_passed,
        "llm_judge_sample_passed": judge_passed,
        "secret_leak_check_passed": True,
        "production_quality_candidate_signal": False,
        "limitations": limitations,
        "probe_errors": probe_errors,
        "source_provider_probe": raw_provider_proof,
    }
    payload["secret_leak_check_passed"] = _secret_leak_check(payload)
    payload["production_quality_candidate_signal"] = all(
        [
            payload["provider_mode"] == "external_verified",
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
    parser.add_argument("--check-readiness", action="store_true")
    parser.add_argument("--provider", default="openai_compatible")
    parser.add_argument("--llm-base-url", default=_env_value("LLM_BASE_URL", "LLM_API_BASE_URL"))
    parser.add_argument("--embedding-model", default=os.getenv("EMBEDDING_MODEL", ""))
    parser.add_argument(
        "--embedding-base-url",
        default=_env_value("EMBEDDING_BASE_URL", "EMBEDDING_API_BASE_URL"),
    )
    parser.add_argument("--llm-model", default=os.getenv("LLM_MODEL", ""))
    parser.add_argument("--redact", action="store_true", help="Retained for explicit CLI safety.")
    parser.add_argument("--fail-on-not-verified", action="store_true")
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

    if args.check_readiness:
        readiness = build_readiness_report()
        print(json.dumps(readiness, indent=2, sort_keys=True))
        return 0 if readiness["readiness_status"] == "ready" else 1

    proof = build_external_provider_proof(
        dry_run=args.dry_run,
        provider=args.provider,
        llm_base_url=args.llm_base_url,
        embedding_base_url=args.embedding_base_url,
        embedding_model=args.embedding_model,
        llm_model=args.llm_model,
    )
    output = _output_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(str(output))
    if args.fail_on_not_verified and proof["provider_mode"] != "external_verified":
        return 1
    return 0 if proof["secret_leak_check_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
