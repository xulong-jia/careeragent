import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import Settings, get_settings
from app.core.errors import AppError


HASH_NAME = "pbkdf2_sha256"
HASH_ITERATIONS = 260_000
FORBIDDEN_PRODUCTION_SECRET_MARKERS = ("dev-only", "replace-me", "change-me")


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        HASH_ITERATIONS,
    )
    return "$".join(
        [
            HASH_NAME,
            str(HASH_ITERATIONS),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        ]
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        name, iterations_text, salt_text, digest_text = password_hash.split("$", 3)
        if name != HASH_NAME:
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations_text),
        )
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def _b64url_encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")


def _b64url_decode(payload: str) -> bytes:
    padding = "=" * (-len(payload) % 4)
    return base64.urlsafe_b64decode((payload + padding).encode("ascii"))


def _auth_secret(settings: Settings | None = None) -> str:
    resolved = settings or get_settings()
    secret = resolved.auth_jwt_secret.strip()
    if not secret:
        raise AppError(
            code="auth_not_configured",
            message="Authentication secret is not configured.",
            status_code=500,
            details={"env": "AUTH_JWT_SECRET"},
        )
    if resolved.app_env == "production":
        if len(secret) < 32:
            raise AppError(
                code="auth_secret_too_short",
                message="Authentication secret is too short for production.",
                status_code=500,
                details={"env": "AUTH_JWT_SECRET", "min_length": 32},
            )
        lowered_secret = secret.lower()
        if any(marker in lowered_secret for marker in FORBIDDEN_PRODUCTION_SECRET_MARKERS):
            raise AppError(
                code="auth_secret_not_allowed",
                message="Authentication secret is a placeholder and cannot be used in production.",
                status_code=500,
                details={"env": "AUTH_JWT_SECRET"},
            )
    return secret


def create_access_token(
    *,
    subject: str,
    email: str,
    role: str,
    workspace_id: str,
    settings: Settings | None = None,
    expires_delta: timedelta | None = None,
) -> tuple[str, datetime]:
    resolved = settings or get_settings()
    secret = _auth_secret(resolved).encode("utf-8")
    now = datetime.now(timezone.utc)
    expires_at = now + (
        expires_delta
        or timedelta(minutes=max(resolved.auth_token_expire_minutes, 1))
    )
    header = {"alg": "HS256", "typ": "JWT"}
    payload: dict[str, Any] = {
        "sub": subject,
        "email": email,
        "role": role,
        "workspace_id": workspace_id,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    signing_input = ".".join(
        [
            _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8")),
            _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")),
        ]
    )
    signature = hmac.new(secret, signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url_encode(signature)}", expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    invalid_error = AppError(
        code="invalid_token",
        message="Invalid or expired authentication token.",
        status_code=401,
        details={},
    )
    try:
        header_text, payload_text, signature_text = token.split(".", 2)
        header = json.loads(_b64url_decode(header_text))
        if header.get("alg") != "HS256":
            raise invalid_error
        signing_input = f"{header_text}.{payload_text}"
        expected_signature = hmac.new(
            _auth_secret().encode("utf-8"),
            signing_input.encode("ascii"),
            hashlib.sha256,
        ).digest()
        actual_signature = _b64url_decode(signature_text)
        if not hmac.compare_digest(actual_signature, expected_signature):
            raise invalid_error
        payload = json.loads(_b64url_decode(payload_text))
        if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
            raise invalid_error
        return payload
    except AppError:
        raise
    except Exception as exc:
        raise invalid_error from exc
