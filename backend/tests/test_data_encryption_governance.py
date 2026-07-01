import json

import pytest

from app.core.config import get_settings
from app.core.crypto import (
    decrypt_json,
    decrypt_text,
    encrypt_json,
    encrypt_text,
    encrypted_envelope_metadata,
    is_encrypted_text,
)
from app.core.errors import AppError


ALT_FERNET_KEY = "bGd9V6Wk0vFEGPz5vp88BDQ2FZhq6UY2zuXm4r7P5lw="


def test_text_and_json_encryption_use_keyed_envelopes(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", ALT_FERNET_KEY)
    monkeypatch.setenv("DATA_ENCRYPTION_KEY_ID", "unit-test-v2")

    try:
        plaintext = "PRIVATE_RESUME_FULL_TEXT alice@example.com"
        encrypted = encrypt_text(plaintext)
        assert encrypted is not None
        assert is_encrypted_text(encrypted)
        assert plaintext not in encrypted
        assert decrypt_text(encrypted) == plaintext

        envelope = json.loads(encrypted)
        assert envelope["key_id"] == "unit-test-v2"
        assert encrypted_envelope_metadata() == {
            "v": 1,
            "key_id": "unit-test-v2",
            "alg": "fernet",
        }

        encrypted_json = encrypt_json({"raw_text": plaintext, "score": 1})
        assert plaintext not in json.dumps(encrypted_json)
        assert decrypt_json(encrypted_json) == {"raw_text": plaintext, "score": 1}
    finally:
        get_settings.cache_clear()


def test_decryption_keeps_legacy_plaintext_compatible():
    legacy = "legacy plaintext row before v3.0"
    assert decrypt_text(legacy) == legacy
    assert decrypt_json({"legacy": True}) == {"legacy": True}


def test_decryption_fails_closed_with_wrong_key(monkeypatch):
    get_settings.cache_clear()
    plaintext = "PRIVATE_JD_FULL_TEXT"
    encrypted = encrypt_text(plaintext)
    assert encrypted is not None

    monkeypatch.setenv("DATA_ENCRYPTION_KEY", ALT_FERNET_KEY)
    monkeypatch.setenv("DATA_ENCRYPTION_KEY_ID", "wrong-key")
    get_settings.cache_clear()

    try:
        with pytest.raises(AppError) as exc_info:
            decrypt_text(encrypted)
        assert exc_info.value.code == "data_decryption_failed"
    finally:
        get_settings.cache_clear()
