from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]


def _load_deployment_validator():
    path = ROOT / "scripts" / "validate_production_deployment.py"
    spec = importlib.util.spec_from_file_location("validate_production_deployment", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_deployment_proof_masks_secrets_and_validates_shape(monkeypatch):
    validator = _load_deployment_validator()
    secret = "test-auth-secret-with-more-than-32-characters"
    data_key = "MKlKIfl6Htn3qasq6OmUZrAptCgKZk_unRl07h5u6Ew="
    monkeypatch.setenv("AUTH_JWT_SECRET", secret)
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", data_key)
    monkeypatch.setenv("POSTGRES_PASSWORD", "test-postgres-password-with-more-than-32-characters")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://careeragent:secret@postgres:5432/careeragent",
    )
    args = SimpleNamespace(
        allow_local_placeholders=False,
        compose_file=str(ROOT / "docker-compose.prod-like.yml"),
        skip_compose=True,
    )

    report = validator.build_report(args)
    rendered = json.dumps(report)

    assert report["status"] == "passed"
    assert report["secrets_masked"] is True
    assert report["private_data_used"] is False
    assert secret not in rendered
    assert data_key not in rendered
    assert "database_url_shape" in {item["name"] for item in report["checks"]}


def test_deployment_proof_fails_without_required_secret(monkeypatch):
    validator = _load_deployment_validator()
    monkeypatch.delenv("AUTH_JWT_SECRET", raising=False)
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", "MKlKIfl6Htn3qasq6OmUZrAptCgKZk_unRl07h5u6Ew=")
    args = SimpleNamespace(
        allow_local_placeholders=True,
        compose_file=str(ROOT / "docker-compose.prod-like.yml"),
        skip_compose=True,
    )

    report = validator.build_report(args)

    assert report["status"] == "failed"
    required = next(item for item in report["checks"] if item["name"] == "required_environment")
    assert required["details"]["missing"] == ["AUTH_JWT_SECRET"]
