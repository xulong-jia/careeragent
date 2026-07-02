#!/usr/bin/env python3
"""Validate runtime AI providers without committing secrets or private data."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.ai.embedding_provider import OpenAICompatibleEmbeddingProvider  # noqa: E402
from app.ai.llm_provider import OpenAICompatibleLLMProvider  # noqa: E402
from app.schemas.jobs import JobProfile  # noqa: E402


LLM_JOB_PROFILE_SCHEMA_PROMPT = """\
Return exactly one valid JSON object for a synthetic, anonymized backend role.
Do not include Markdown, code fences, comments, private data, emails, phone numbers or real company names.

The JSON object must validate against this JobProfile shape and must include every key below:
- job_profile_id: non-empty string, for example "provider_probe_backend_001"
- job_title: string
- company: anonymized string
- location: string
- role_category: string
- required_skills: array of strings
- preferred_skills: array of strings
- responsibilities: array of strings
- business_scenarios: array of strings
- hidden_requirements: array of objects
- interview_focus: array of strings
- risk_level: string, one of "low", "medium" or "high"
- summary: string
- parse_confidence: number between 0 and 1
- evidence: array of objects
- warnings: array of strings
- parser_metadata: object

Use safe synthetic content only. Keep the response concise but complete.
"""


def _mask(value: str) -> str:
    return f"[set length={len(value)}]" if value else ""


def _redact_message(message: str) -> str:
    redacted = message
    for secret in (_env("LLM_API_KEY"), _env("EMBEDDING_API_KEY")):
        if secret:
            redacted = redacted.replace(secret, "[redacted]")
    redacted = re.sub(r"sk-[A-Za-z0-9_-]{8,}", "[redacted]", redacted)
    redacted = re.sub(
        r"(?i)(authorization:\s*bearer\s+)[^\s,;]+",
        r"\1[redacted]",
        redacted,
    )
    return redacted


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def _validate_llm() -> dict[str, Any]:
    base_url = _env("LLM_API_BASE_URL")
    api_key = _env("LLM_API_KEY")
    model = _env("LLM_MODEL")
    if not base_url or not api_key or not model:
        return {"status": "skipped", "reason": "missing_llm_config"}
    provider = OpenAICompatibleLLMProvider(
        api_base_url=base_url,
        api_key=api_key,
        model=model,
        timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "10")),
    )
    output = provider.generate_structured(
        prompt=LLM_JOB_PROFILE_SCHEMA_PROMPT,
        schema=JobProfile,
        max_output_length=4000,
    )
    return {
        "status": "pass",
        "provider": provider.name,
        "model": model,
        "api_base_url": _mask(base_url),
        "schema_validated": True,
        "role_category": output.role_category,
    }


def _validate_embedding() -> dict[str, Any]:
    base_url = _env("EMBEDDING_API_BASE_URL")
    api_key = _env("EMBEDDING_API_KEY")
    model = _env("EMBEDDING_MODEL")
    dimension = int(os.getenv("EMBEDDING_DIMENSION", "384"))
    if not base_url or not api_key or not model:
        return {"status": "skipped", "reason": "missing_embedding_config"}
    provider = OpenAICompatibleEmbeddingProvider(
        api_base_url=base_url,
        api_key=api_key,
        model=model,
        timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "10")),
        dimension=dimension,
    )
    vector = provider.embed_text("anonymized provider validation probe")
    return {
        "status": "pass",
        "provider": provider.name,
        "model": model,
        "api_base_url": _mask(base_url),
        "dimension": len(vector),
        "vector_nonzero": any(value != 0 for value in vector),
    }


def build_provider_proof(*, require_provider: bool = False) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    for name, validate in {"llm": _validate_llm, "embedding": _validate_embedding}.items():
        try:
            checks[name] = validate()
        except Exception as exc:  # pragma: no cover - message only, no secret values
            checks[name] = {
                "status": "fail",
                "error_type": type(exc).__name__,
                "message": _redact_message(str(exc)),
            }
    passed = all(item.get("status") == "pass" for item in checks.values())
    skipped = any(item.get("status") == "skipped" for item in checks.values())
    provider_mode = "provider_verified" if passed else "offline" if skipped else "failed"
    if require_provider and provider_mode != "provider_verified":
        status = "fail"
    else:
        status = "pass" if provider_mode != "failed" else "fail"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "provider_mode": provider_mode,
        "checks": checks,
        "secrets_masked": True,
        "private_data_used": False,
        "proof_boundary": (
            "This artifact proves the configured runtime path only. Keep real provider "
            "keys and outputs outside Git."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-provider", action="store_true")
    args = parser.parse_args()
    proof = build_provider_proof(require_provider=args.require_provider)
    payload = json.dumps(proof, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0 if proof["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
