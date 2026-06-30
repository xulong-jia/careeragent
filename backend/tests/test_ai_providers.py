import json

import pytest
from pydantic import BaseModel

from app.ai.embedding_provider import (
    DeterministicEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
    build_embedding_provider,
)
from app.ai.llm_provider import (
    DeterministicLLMProvider,
    OpenAICompatibleLLMProvider,
    build_llm_provider,
)
from app.core.config import get_settings
from app.core.errors import AppError


class SyntheticLLMOutput(BaseModel):
    summary: str
    confidence: float


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class _FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_deterministic_llm_default_validates_fallback_without_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    get_settings.cache_clear()

    provider = build_llm_provider()
    result = provider.generate_structured(
        prompt="Synthetic prompt",
        schema=SyntheticLLMOutput,
        fallback={"summary": "deterministic", "confidence": 1.0},
    )

    assert isinstance(provider, DeterministicLLMProvider)
    assert result.summary == "deterministic"


def test_real_llm_disabled_without_key_uses_deterministic(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("ENABLE_REAL_LLM", "false")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    get_settings.cache_clear()

    assert isinstance(build_llm_provider(), DeterministicLLMProvider)


def test_real_llm_missing_key_returns_controlled_error(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setenv("LLM_API_BASE_URL", "https://provider.example/v1")
    monkeypatch.setenv("LLM_MODEL", "synthetic-model")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    get_settings.cache_clear()

    with pytest.raises(AppError) as exc_info:
        build_llm_provider()

    assert exc_info.value.code == "ai_provider_config_error"
    assert "API" not in exc_info.value.message
    assert "sk-" not in exc_info.value.message


def test_fake_openai_compatible_llm_response_is_schema_validated(monkeypatch):
    def fake_urlopen(request, timeout):
        assert timeout == 3
        assert request.headers["Authorization"].startswith("Bearer ")
        return _FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {"summary": "provider ok", "confidence": 0.9}
                            )
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = OpenAICompatibleLLMProvider(
        api_base_url="https://provider.example/v1",
        api_key="sk-testsecret123456789",
        model="synthetic-model",
        timeout_seconds=3,
    )

    result = provider.generate_structured(
        prompt="Return JSON only.",
        schema=SyntheticLLMOutput,
        max_output_length=200,
    )

    assert result.summary == "provider ok"
    assert result.confidence == 0.9


def test_invalid_llm_json_fails_schema_validation(monkeypatch):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: _FakeResponse(
            {"choices": [{"message": {"content": "not-json"}}]}
        ),
    )
    provider = OpenAICompatibleLLMProvider(
        api_base_url="https://provider.example/v1",
        api_key="sk-testsecret123456789",
        model="synthetic-model",
        timeout_seconds=3,
    )

    with pytest.raises(AppError) as exc_info:
        provider.generate_structured(prompt="Return JSON.", schema=SyntheticLLMOutput)

    assert exc_info.value.code == "ai_schema_validation_failed"


def test_deterministic_embedding_is_stable_and_dimensioned():
    provider = DeterministicEmbeddingProvider(dimension=16)

    first = provider.embed_text("FastAPI RAG testing")
    second = provider.embed_text("FastAPI RAG testing")

    assert first == second
    assert len(first) == 16
    assert any(value for value in first)


def test_embedding_empty_input_returns_controlled_error():
    provider = DeterministicEmbeddingProvider(dimension=16)

    with pytest.raises(AppError) as exc_info:
        provider.embed_text("   ")

    assert exc_info.value.code == "embedding_input_empty"


def test_real_embedding_disabled_without_key_uses_deterministic(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai_compatible")
    monkeypatch.setenv("ENABLE_REAL_EMBEDDING", "false")
    monkeypatch.delenv("EMBEDDING_API_KEY", raising=False)
    get_settings.cache_clear()

    assert isinstance(build_embedding_provider(), DeterministicEmbeddingProvider)


def test_real_embedding_missing_key_returns_controlled_error(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai_compatible")
    monkeypatch.setenv("ENABLE_REAL_EMBEDDING", "true")
    monkeypatch.setenv("EMBEDDING_API_BASE_URL", "https://provider.example/v1")
    monkeypatch.setenv("EMBEDDING_MODEL", "synthetic-embedding")
    monkeypatch.delenv("EMBEDDING_API_KEY", raising=False)
    get_settings.cache_clear()

    with pytest.raises(AppError) as exc_info:
        build_embedding_provider()

    assert exc_info.value.code == "embedding_provider_config_error"
    assert "sk-" not in exc_info.value.message


def test_fake_openai_compatible_embedding_response(monkeypatch):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: _FakeResponse({"data": [{"embedding": [0.1, 0.2]}]}),
    )
    provider = OpenAICompatibleEmbeddingProvider(
        api_base_url="https://provider.example/v1",
        api_key="sk-testsecret123456789",
        model="synthetic-embedding",
        timeout_seconds=3,
        dimension=2,
    )

    assert provider.embed_text("FastAPI") == [0.1, 0.2]
