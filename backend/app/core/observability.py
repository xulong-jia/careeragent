from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qsl, urlencode

from app.core.config import Settings
from app.core.privacy import mask_secret, redact_mapping, redact_text


REDACTED = "[redacted]"
SENSITIVE_EVENT_KEYS = {
    "authorization",
    "cookie",
    "cookies",
    "data",
    "body",
    "request_body",
    "api_key",
    "apikey",
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "resume_text",
    "jd_text",
    "jd_raw_text",
    "interview_answer",
    "answer_text",
    "chunk_text",
    "raw_text",
    "full_text",
    "user_text",
}
SENSITIVE_QUERY_PARTS = ("token", "key", "secret", "password")


def _sensitive_key(key: object) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return any(part in normalized for part in SENSITIVE_EVENT_KEYS)


def _scrub_query_string(value: object) -> str:
    pairs = []
    for key, item in parse_qsl(str(value or ""), keep_blank_values=True):
        if any(part in key.lower() for part in SENSITIVE_QUERY_PARTS):
            pairs.append((key, REDACTED))
        else:
            pairs.append((key, mask_secret(item)))
    return urlencode(pairs)


def _scrub_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _sensitive_key(key_text):
                redacted[key_text] = REDACTED
            elif key_text == "query_string":
                redacted[key_text] = _scrub_query_string(item)
            else:
                redacted[key_text] = _scrub_value(item)
        return redacted
    if isinstance(value, list):
        return [_scrub_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_scrub_value(item) for item in value)
    if isinstance(value, str):
        if len(value) > 500:
            return redact_text(value)
        return mask_secret(value)
    return value


def scrub_sentry_event(
    event: dict[str, Any],
    hint: object | None = None,
) -> dict[str, Any]:
    scrubbed = _scrub_value(redact_mapping(event))
    if not isinstance(scrubbed, dict):
        return {}

    request = scrubbed.get("request")
    if isinstance(request, dict):
        request.pop("data", None)
        request.pop("body", None)
        request.pop("cookies", None)
        headers = request.get("headers")
        if isinstance(headers, dict):
            for key in list(headers):
                if str(key).lower() in {"authorization", "cookie", "set-cookie"}:
                    headers[key] = REDACTED
    scrubbed.pop("user", None)
    return scrubbed


def scrub_sentry_transaction(
    event: dict[str, Any],
    hint: object | None = None,
) -> dict[str, Any]:
    return scrub_sentry_event(event, hint)


def initialize_sentry(settings: Settings) -> bool:
    if not settings.sentry_dsn:
        return False

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        release=settings.sentry_release or None,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=settings.sentry_send_default_pii,
        before_send=scrub_sentry_event,
        before_send_transaction=scrub_sentry_transaction,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
    )
    return True
