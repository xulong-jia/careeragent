import pytest

from app.core.config import get_settings
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
