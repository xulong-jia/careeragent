from fastapi.testclient import TestClient


def test_initialize_sentry_without_dsn_is_disabled(monkeypatch):
    from app.core.config import get_settings
    from app.core.observability import initialize_sentry

    monkeypatch.delenv("SENTRY_DSN", raising=False)
    get_settings.cache_clear()

    assert initialize_sentry(get_settings()) is False

    get_settings.cache_clear()


def test_sentry_send_default_pii_is_rejected(monkeypatch):
    from app.core.config import get_settings, validate_runtime_settings

    monkeypatch.setenv("SENTRY_SEND_DEFAULT_PII", "true")
    get_settings.cache_clear()

    try:
        try:
            validate_runtime_settings(get_settings())
        except RuntimeError as exc:
            assert "SENTRY_SEND_DEFAULT_PII" in str(exc)
        else:
            raise AssertionError("SENTRY_SEND_DEFAULT_PII=true should be rejected")
    finally:
        get_settings.cache_clear()


def test_sentry_before_send_scrubs_sensitive_payload():
    from app.core.observability import REDACTED, scrub_sentry_event

    event = {
        "message": "User jane@example.com called +1 415 555 1212",
        "user": {"email": "jane@example.com"},
        "request": {
            "headers": {
                "Authorization": "Bearer secret-token",
                "Cookie": "session=secret-cookie",
                "X-Request-ID": "safe-request-id",
            },
            "data": {"resume_text": "raw resume content"},
            "query_string": "token=secret-token&search=jane@example.com",
        },
        "contexts": {
            "payload": {
                "resume_text": "raw resume content",
                "jd_text": "raw jd content",
                "interview_answer": "raw answer content",
                "chunk_text": "raw chunk content",
                "raw_text": "raw user text",
            }
        },
    }

    scrubbed = scrub_sentry_event(event)
    dumped = str(scrubbed)

    assert scrubbed["request"]["headers"]["Authorization"] == REDACTED
    assert scrubbed["request"]["headers"]["Cookie"] == REDACTED
    assert "data" not in scrubbed["request"]
    assert "user" not in scrubbed
    assert "secret-token" not in dumped
    assert "secret-cookie" not in dumped
    assert "jane@example.com" not in dumped
    assert "415 555 1212" not in dumped
    assert "raw resume content" not in dumped
    assert "raw jd content" not in dumped
    assert "raw answer content" not in dumped
    assert "raw chunk content" not in dumped
    assert "raw user text" not in dumped


def test_cors_allows_sentry_trace_headers_without_header_wildcard():
    from app.main import CORS_ALLOW_HEADERS, app

    assert "*" not in CORS_ALLOW_HEADERS
    assert "sentry-trace" in CORS_ALLOW_HEADERS
    assert "baggage" in CORS_ALLOW_HEADERS

    response = TestClient(app).options(
        "/live",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": (
                "sentry-trace,baggage,authorization,x-observability-test"
            ),
        },
    )

    assert response.status_code == 200
    allowed = response.headers["access-control-allow-headers"].lower()
    assert "*" not in allowed
    assert "sentry-trace" in allowed
    assert "baggage" in allowed
    assert "authorization" in allowed
    assert "x-observability-test" in allowed


def test_observability_test_error_endpoint_default_closed():
    from app.main import app

    response = TestClient(app, raise_server_exceptions=False).post(
        "/api/observability/test-error",
        headers={"X-Observability-Test": "enabled"},
    )

    assert response.status_code == 404


def test_observability_test_error_endpoint_requires_header(monkeypatch):
    from app.core.config import get_settings
    from app.main import create_app

    monkeypatch.setenv("ENABLE_OBSERVABILITY_TEST_ENDPOINT", "true")
    get_settings.cache_clear()
    client = TestClient(create_app(), raise_server_exceptions=False)

    response = client.post("/api/observability/test-error")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "observability_test_forbidden"

    get_settings.cache_clear()


def test_observability_test_error_endpoint_raises_synthetic_error(monkeypatch):
    from app.core.config import get_settings
    from app.main import create_app

    monkeypatch.setenv("ENABLE_OBSERVABILITY_TEST_ENDPOINT", "true")
    get_settings.cache_clear()
    client = TestClient(create_app(), raise_server_exceptions=False)

    response = client.post(
        "/api/observability/test-error",
        headers={"X-Observability-Test": "enabled"},
    )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_server_error"

    get_settings.cache_clear()
