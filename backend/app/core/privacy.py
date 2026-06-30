from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from typing import Any


EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
SECRET_PATTERN = re.compile(
    r"(?i)\b(?:OPENAI_API_KEY|api[_-]?key|token|secret|password)\b\s*[:=]\s*['\"]?[^'\"\s]+"
)
OPENAI_KEY_PATTERN = re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b")

SENSITIVE_KEY_PARTS = {
    "api_key",
    "apikey",
    "answer_text",
    "chunk_text",
    "full_text",
    "interview_notes",
    "jd_raw_text",
    "password",
    "raw_text",
    "reflection",
    "resume_text",
    "secret",
    "token",
}


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _mask_inline_secrets(value: str) -> str:
    masked = EMAIL_PATTERN.sub("[redacted-email]", value)
    masked = PHONE_PATTERN.sub("[redacted-phone]", masked)
    masked = SECRET_PATTERN.sub("[redacted-secret]", masked)
    return OPENAI_KEY_PATTERN.sub("[redacted-secret]", masked)


def safe_preview(value: object, max_chars: int = 120) -> str:
    text = "" if value is None else str(value)
    masked = _mask_inline_secrets(text.strip())
    if len(masked) <= max_chars:
        return masked
    return f"{masked[: max_chars - 3].rstrip()}..."


def redact_text(value: object, max_preview: int = 120) -> str:
    text = "" if value is None else str(value)
    return (
        f"[redacted length={len(text)} sha256={_hash_text(text)} "
        f'preview="{safe_preview(text, max_preview)}"]'
    )


def _is_sensitive_key(key: object) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def _needs_string_redaction(value: str) -> bool:
    return (
        len(value) > 500
        or EMAIL_PATTERN.search(value) is not None
        or PHONE_PATTERN.search(value) is not None
        or SECRET_PATTERN.search(value) is not None
        or OPENAI_KEY_PATTERN.search(value) is not None
    )


def redact_mapping(payload: Any, *, max_preview: int = 120) -> Any:
    if isinstance(payload, Mapping):
        redacted: dict[str, Any] = {}
        for key, value in payload.items():
            key_text = str(key)
            if _is_sensitive_key(key_text):
                redacted[key_text] = redact_text(value, max_preview=max_preview)
            else:
                redacted[key_text] = redact_mapping(value, max_preview=max_preview)
        return redacted
    if isinstance(payload, str):
        if _needs_string_redaction(payload):
            return redact_text(payload, max_preview=max_preview)
        return _mask_inline_secrets(payload)
    if isinstance(payload, Sequence) and not isinstance(payload, (bytes, bytearray)):
        return [redact_mapping(item, max_preview=max_preview) for item in payload]
    return payload
