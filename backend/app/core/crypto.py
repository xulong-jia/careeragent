from __future__ import annotations

import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import LOCAL_DEV_DATA_ENCRYPTION_KEY, get_settings
from app.core.errors import AppError


ENVELOPE_VERSION = 1
ENVELOPE_ALG = "fernet"


def _settings_key() -> tuple[str, str]:
    settings = get_settings()
    key = settings.data_encryption_key or LOCAL_DEV_DATA_ENCRYPTION_KEY
    key_id = settings.data_encryption_key_id or "local-dev-v1"
    try:
        Fernet(key.encode("utf-8"))
    except Exception as exc:
        raise AppError(
            code="data_encryption_key_invalid",
            message="Data encryption key is invalid.",
            status_code=500,
            details={"env": "DATA_ENCRYPTION_KEY"},
        ) from exc
    return key, key_id


def _fernet() -> tuple[Fernet, str]:
    key, key_id = _settings_key()
    return Fernet(key.encode("utf-8")), key_id


def _is_text_envelope(value: object) -> bool:
    return (
        isinstance(value, dict)
        and value.get("v") == ENVELOPE_VERSION
        and value.get("alg") == ENVELOPE_ALG
        and isinstance(value.get("ciphertext"), str)
    )


def _load_text_envelope(value: str) -> dict[str, object] | None:
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return None
    return parsed if _is_text_envelope(parsed) else None


def encrypted_envelope_metadata() -> dict[str, object]:
    _key, key_id = _settings_key()
    return {"v": ENVELOPE_VERSION, "key_id": key_id, "alg": ENVELOPE_ALG}


def encrypt_text(value: str | None) -> str | None:
    if value is None:
        return None
    if _load_text_envelope(value):
        return value
    fernet, key_id = _fernet()
    token = fernet.encrypt(value.encode("utf-8")).decode("ascii")
    return json.dumps(
        {"v": ENVELOPE_VERSION, "key_id": key_id, "alg": ENVELOPE_ALG, "ciphertext": token},
        separators=(",", ":"),
        sort_keys=True,
    )


def decrypt_text(value: str | None) -> str:
    if value is None:
        return ""
    envelope = _load_text_envelope(value)
    if not envelope:
        return value
    fernet, _key_id = _fernet()
    try:
        return fernet.decrypt(str(envelope["ciphertext"]).encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise AppError(
            code="data_decryption_failed",
            message="Encrypted data could not be decrypted with the configured key.",
            status_code=500,
            details={"key_id": envelope.get("key_id")},
        ) from exc


def encrypt_json(value: Any) -> dict[str, object]:
    if _is_text_envelope(value):
        return dict(value)
    fernet, key_id = _fernet()
    plaintext = json.dumps(value, default=str, separators=(",", ":"), sort_keys=True)
    token = fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")
    return {"v": ENVELOPE_VERSION, "key_id": key_id, "alg": ENVELOPE_ALG, "ciphertext": token}


def decrypt_json(value: Any) -> Any:
    if not _is_text_envelope(value):
        return value
    fernet, _key_id = _fernet()
    try:
        plaintext = fernet.decrypt(str(value["ciphertext"]).encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise AppError(
            code="data_decryption_failed",
            message="Encrypted JSON data could not be decrypted with the configured key.",
            status_code=500,
            details={"key_id": value.get("key_id")},
        ) from exc
    return json.loads(plaintext)


def is_encrypted_text(value: object) -> bool:
    return isinstance(value, str) and _load_text_envelope(value) is not None
