#!/usr/bin/env python3
"""Check private env readiness for external provider proof execution."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse


REQUIRED_VARS = [
    "AI_PROVIDER_MODE",
    "LLM_PROVIDER",
    "LLM_BASE_URL",
    "LLM_MODEL",
    "LLM_API_KEY",
    "EMBEDDING_PROVIDER",
    "EMBEDDING_BASE_URL",
    "EMBEDDING_MODEL",
    "EMBEDDING_API_KEY",
    "DATA_ENCRYPTION_KEY",
    "AUTH_JWT_SECRET",
]
SECRET_VARS = {
    "LLM_API_KEY",
    "EMBEDDING_API_KEY",
    "DATA_ENCRYPTION_KEY",
    "AUTH_JWT_SECRET",
}
SAFE_PROVIDER_MODES = {"provider_verified", "external_verified"}
SAFE_PROVIDERS = {"openai_compatible", "generic_http"}
UNSAFE_MARKERS = ("change-me", "dev-only", "replace-me", "placeholder", "local-dev")
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]+"),
    re.compile(r"ghp_[A-Za-z0-9_]+"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mask(value: str) -> str:
    if not value:
        return "[missing]"
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"[set length={len(value)} sha256:{digest}]"


def _is_local_url(value: str) -> bool:
    host = urlparse(value).hostname or ""
    return host in {"localhost", "0.0.0.0"} or host.startswith("127.")


def _unsafe_config(env: dict[str, str]) -> list[str]:
    issues: list[str] = []
    mode = env.get("AI_PROVIDER_MODE", "")
    if mode and mode not in SAFE_PROVIDER_MODES:
        issues.append("AI_PROVIDER_MODE must be provider_verified or external_verified.")
    for key in ("LLM_PROVIDER", "EMBEDDING_PROVIDER"):
        value = env.get(key, "")
        if value and value not in SAFE_PROVIDERS:
            issues.append(f"{key} must be openai_compatible or generic_http.")
    for key in ("LLM_BASE_URL", "EMBEDDING_BASE_URL"):
        value = env.get(key, "")
        if value and _is_local_url(value):
            issues.append(f"{key} points to localhost; this is not external provider proof.")
    for key in SECRET_VARS:
        value = env.get(key, "").lower()
        if value and any(marker in value for marker in UNSAFE_MARKERS):
            issues.append(f"{key} looks like a placeholder/dev secret.")
    return issues


def _summary(env: dict[str, str]) -> dict[str, Any]:
    return {
        key: {
            "present": bool(env.get(key)),
            "value": _mask(env.get(key, "")) if key in SECRET_VARS or key.endswith("URL") else env.get(key, ""),
        }
        for key in REQUIRED_VARS
    }


def _secret_leak_check(payload: dict[str, Any], env: dict[str, str]) -> bool:
    rendered = json.dumps(payload, sort_keys=True)
    for key in SECRET_VARS:
        secret = env.get(key)
        if secret and secret in rendered:
            return False
    return not any(pattern.search(rendered) for pattern in SECRET_PATTERNS)


def build_readiness_report(env: dict[str, str] | None = None) -> dict[str, Any]:
    env = dict(env or os.environ)
    missing = [key for key in REQUIRED_VARS if not env.get(key, "").strip()]
    unsafe = _unsafe_config(env)
    if missing:
        readiness_status = "missing_required_env"
    elif unsafe:
        readiness_status = "unsafe_config"
    else:
        readiness_status = "ready"
    report: dict[str, Any] = {
        "generated_at": _utc_now(),
        "readiness_status": readiness_status,
        "missing_vars": missing,
        "unsafe_config": unsafe,
        "masked_config_summary": _summary(env),
        "next_command_to_run": (
            "PYTHONPATH=backend backend/.venv/bin/python "
            "scripts/run_external_provider_proof.py "
            "--provider openai_compatible "
            "--llm-base-url \"$LLM_BASE_URL\" "
            "--llm-model \"$LLM_MODEL\" "
            "--embedding-base-url \"$EMBEDDING_BASE_URL\" "
            "--embedding-model \"$EMBEDDING_MODEL\" "
            "--output evidence/private_outputs/provider_proof.$(date +%Y%m%d-%H%M%S).json "
            "--redact --fail-on-not-verified"
        ),
        "secret_leak_check_passed": True,
    }
    report["secret_leak_check_passed"] = _secret_leak_check(report, env)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_readiness_report()
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
        print(str(args.output))
    else:
        print(payload, end="")
    return 0 if report["readiness_status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
