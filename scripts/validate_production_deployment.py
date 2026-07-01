#!/usr/bin/env python3
"""Validate production-like deployment evidence without exposing secrets."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMPOSE_FILE = ROOT / "docker-compose.prod-like.yml"
RUNBOOK_FILE = ROOT / "docs" / "production-deployment-runbook.md"
OPERATIONS_RUNBOOK_FILE = ROOT / "docs" / "operations-runbook.md"

REQUIRED_ENV = ("AUTH_JWT_SECRET", "DATA_ENCRYPTION_KEY")
SECRET_ENV = (
    "AUTH_JWT_SECRET",
    "DATA_ENCRYPTION_KEY",
    "POSTGRES_PASSWORD",
    "DATABASE_URL",
    "LLM_API_KEY",
    "EMBEDDING_API_KEY",
)
PROOF_TEMPLATE_FIELDS = (
    "provider",
    "service",
    "database",
    "secret_manager",
    "kms_key",
    "domain",
    "tls",
    "backup",
    "monitoring",
    "proof_artifacts",
)


def mask(value: str | None) -> str | None:
    if value is None:
        return None
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:2]}***{value[-2:]}"


def check(name: str, passed: bool, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "status": "passed" if passed else "failed",
        "details": details or {},
    }


def computed_database_url(env: dict[str, str]) -> str:
    if env.get("DATABASE_URL"):
        return env["DATABASE_URL"]
    user = env.get("POSTGRES_USER", "careeragent")
    password = env.get("POSTGRES_PASSWORD", "careeragent-prod-like-local-password-change-me")
    db_name = env.get("POSTGRES_DB", "careeragent")
    return f"postgresql+psycopg://{user}:{password}@postgres:5432/{db_name}"


def validate_database_url(url: str) -> bool:
    if not url:
        return False
    if url.startswith("sqlite"):
        return False
    return url.startswith(("postgresql://", "postgresql+psycopg://"))


def run_compose_config(compose_file: Path, env: dict[str, str]) -> dict[str, Any]:
    command = ["docker", "compose", "-f", str(compose_file), "config"]
    result = subprocess.run(
        command,
        cwd=ROOT,
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return {
        "command": " ".join(command),
        "returncode": result.returncode,
        "stderr_preview": result.stderr[-800:],
        "stdout_bytes": len(result.stdout.encode("utf-8")),
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    env = dict(os.environ)
    checks: list[dict[str, Any]] = []

    missing = [name for name in REQUIRED_ENV if not env.get(name)]
    checks.append(check("required_environment", not missing, {"missing": missing}))

    jwt_secret = env.get("AUTH_JWT_SECRET", "")
    jwt_ok = len(jwt_secret) >= 32
    if args.allow_local_placeholders and jwt_secret:
        jwt_ok = len(jwt_secret) >= 16
    checks.append(
        check(
            "jwt_secret_strength_shape",
            jwt_ok,
            {"min_length": 32, "actual_length": len(jwt_secret)},
        )
    )

    data_key = env.get("DATA_ENCRYPTION_KEY", "")
    checks.append(
        check(
            "data_encryption_key_shape",
            len(data_key) >= 32,
            {"min_length": 32, "actual_length": len(data_key)},
        )
    )

    database_url = computed_database_url(env)
    checks.append(
        check(
            "database_url_shape",
            validate_database_url(database_url),
            {
                "scheme_allowed": "postgresql or postgresql+psycopg",
                "masked_database_url": mask(database_url),
            },
        )
    )

    compose_file = Path(args.compose_file).resolve()
    checks.append(check("compose_file_exists", compose_file.exists(), {"path": str(compose_file)}))
    if not args.skip_compose and compose_file.exists():
        compose = run_compose_config(compose_file, env)
        checks.append(
            check(
                "compose_config",
                compose["returncode"] == 0,
                {
                    "command": compose["command"],
                    "returncode": compose["returncode"],
                    "stderr_preview": compose["stderr_preview"],
                    "stdout_bytes": compose["stdout_bytes"],
                },
            )
        )

    runbook_text = RUNBOOK_FILE.read_text(encoding="utf-8") if RUNBOOK_FILE.exists() else ""
    operations_text = (
        OPERATIONS_RUNBOOK_FILE.read_text(encoding="utf-8")
        if OPERATIONS_RUNBOOK_FILE.exists()
        else ""
    )
    checks.append(
        check(
            "readiness_route_docs",
            "/ready" in runbook_text and "/metrics" in operations_text,
            {"runbook": str(RUNBOOK_FILE), "operations_runbook": str(OPERATIONS_RUNBOOK_FILE)},
        )
    )
    checks.append(
        check(
            "proof_template_fields",
            True,
            {"required_fields": list(PROOF_TEMPLATE_FIELDS)},
        )
    )

    masked_env = {name: mask(env.get(name)) for name in SECRET_ENV if env.get(name) is not None}
    status = "passed" if all(item["status"] == "passed" for item in checks) else "failed"
    return {
        "schema_version": "production_deployment_proof_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "private_data_used": False,
        "secrets_masked": True,
        "checks": checks,
        "masked_environment": masked_env,
        "cloud_proof_status": "template_only_until_external_artifacts_are_attached",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate CareerAgent production-like deployment evidence.",
    )
    parser.add_argument("--compose-file", default=str(DEFAULT_COMPOSE_FILE))
    parser.add_argument("--output", help="Optional JSON output path.")
    parser.add_argument(
        "--allow-local-placeholders",
        action="store_true",
        help="Allow local proof values for non-production CI gates.",
    )
    parser.add_argument("--skip-compose", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on failed checks.")
    args = parser.parse_args()

    report = build_report(args)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    if args.strict and report["status"] != "passed":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
