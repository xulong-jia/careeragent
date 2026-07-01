import pytest

from app.core.config import get_settings, settings_summary, validate_runtime_settings
from app.core.errors import AppError
from app.core.security import create_access_token


def test_production_app_env_is_normalized_for_auth_secret_checks(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "Production")
    monkeypatch.setenv("AUTH_JWT_SECRET", "short")

    try:
        settings = get_settings()
        assert settings.app_env == "production"
        with pytest.raises(AppError) as exc_info:
            create_access_token(
                subject="user_1",
                email="user@example.com",
                role="user",
                workspace_id="workspace_1",
                settings=settings,
            )
        assert exc_info.value.code == "auth_secret_too_short"
    finally:
        get_settings.cache_clear()


def test_production_rejects_dev_only_auth_secret(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "AUTH_JWT_SECRET",
        "dev-only-change-me-careeragent-local-auth-secret-32chars",
    )

    try:
        settings = get_settings()
        with pytest.raises(AppError) as exc_info:
            create_access_token(
                subject="user_1",
                email="user@example.com",
                role="user",
                workspace_id="workspace_1",
                settings=settings,
            )
        assert exc_info.value.code == "auth_secret_not_allowed"
    finally:
        get_settings.cache_clear()


def test_local_dev_accepts_dev_only_auth_secret(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv(
        "AUTH_JWT_SECRET",
        "dev-only-change-me-careeragent-local-auth-secret-32chars",
    )
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./local_data/careeragent.db")

    try:
        settings = get_settings()
        validate_runtime_settings(settings)
        assert settings.app_env == "development"
    finally:
        get_settings.cache_clear()


def test_production_runtime_validation_rejects_sqlite(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_JWT_SECRET", "prod-secret-value-with-more-than-32-chars")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./local_data/careeragent.db")

    try:
        with pytest.raises(RuntimeError, match="SQLite"):
            validate_runtime_settings(get_settings())
    finally:
        get_settings.cache_clear()


def test_production_runtime_validation_requires_data_encryption_key(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_JWT_SECRET", "prod-secret-value-with-more-than-32-chars")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@db/careeragent")
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "https://careeragent.example.com")
    monkeypatch.delenv("DATA_ENCRYPTION_KEY", raising=False)

    try:
        with pytest.raises(RuntimeError, match="DATA_ENCRYPTION_KEY"):
            validate_runtime_settings(get_settings())
    finally:
        get_settings.cache_clear()


def test_production_runtime_validation_rejects_dev_data_encryption_key(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_JWT_SECRET", "prod-secret-value-with-more-than-32-chars")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@db/careeragent")
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "https://careeragent.example.com")
    monkeypatch.setenv(
        "DATA_ENCRYPTION_KEY",
        "MKlKIfl6Htn3qasq6OmUZrAptCgKZk_unRl07h5u6Ew=",
    )
    monkeypatch.setenv("DATA_ENCRYPTION_KEY_ID", "local-dev-v1")

    try:
        with pytest.raises(RuntimeError, match="DATA_ENCRYPTION_KEY"):
            validate_runtime_settings(get_settings())
    finally:
        get_settings.cache_clear()


def test_config_summary_masks_secret_values(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AUTH_JWT_SECRET", "visible-secret-value")
    monkeypatch.setenv("LLM_API_KEY", "sk-testsecret123456789")
    monkeypatch.setenv("EMBEDDING_API_KEY", "embedding-secret")

    try:
        summary = settings_summary(get_settings())
        dumped = str(summary)
        assert "visible-secret-value" not in dumped
        assert "sk-testsecret" not in dumped
        assert "embedding-secret" not in dumped
        assert summary["auth_jwt_secret"] == "[set length=20]"
        assert summary["data_encryption_key"] != get_settings().data_encryption_key
        assert summary["data_encryption_key_id"]
    finally:
        get_settings.cache_clear()
