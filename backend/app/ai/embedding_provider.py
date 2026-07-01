from __future__ import annotations

import hashlib
import json
import math
import re
import urllib.error
import urllib.request
from typing import Any

from app.core.config import Settings, get_settings
from app.core.errors import AppError


MAX_EMBEDDING_INPUT_CHARS = 20000


class LocalVectorEmbeddingProvider:
    name = "local_bow"
    semantic = False
    vector_source = "local_bow_hash"

    def __init__(
        self,
        *,
        dimension: int = 384,
        model: str = "local-bow-v1",
        provider_config_id: str = "local-bow-default",
    ) -> None:
        if dimension <= 0:
            raise AppError(
                code="embedding_provider_config_error",
                message="Embedding dimension must be greater than zero.",
                status_code=500,
            )
        self.dimension = dimension
        self.model = model
        self.version = "local-bow-v1"
        self.provider_config_id = provider_config_id

    def embed_text(self, text: str) -> list[float]:
        normalized = _normalize_input(text)
        vector = [0.0] * self.dimension
        for token in _tokenize(normalized):
            index = _feature_index(token, self.dimension)
            vector[index] += 1.0
        return _normalize_vector(vector)


class DeterministicEmbeddingProvider(LocalVectorEmbeddingProvider):
    name = "deterministic"


class LocalSemanticEmbeddingProvider(LocalVectorEmbeddingProvider):
    name = "local_semantic"
    semantic = True
    vector_source = "local_semantic_hash"

    def __init__(
        self,
        *,
        dimension: int = 384,
        model: str = "local-semantic-v1",
        provider_config_id: str = "local-semantic-default",
    ) -> None:
        super().__init__(
            dimension=dimension,
            model=model,
            provider_config_id=provider_config_id,
        )
        self.version = "local-semantic-v1"

    def embed_text(self, text: str) -> list[float]:
        normalized = _normalize_input(text)
        vector = [0.0] * self.dimension
        tokens = _tokenize(normalized)
        features = set(tokens)
        for token in tokens:
            features.update(_semantic_features(token))
        for feature in features:
            index = _feature_index(feature, self.dimension)
            vector[index] += 1.0
        return _normalize_vector(vector)


class OpenAICompatibleEmbeddingProvider:
    name = "openai_compatible"
    semantic = True
    vector_source = "provider_embedding"

    def __init__(
        self,
        *,
        api_base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
        dimension: int,
        provider_config_id: str = "openai-compatible",
        retry_count: int = 1,
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.dimension = dimension
        self.version = model
        self.provider_config_id = provider_config_id
        self.retry_count = retry_count

    def embed_text(self, text: str) -> list[float]:
        normalized = _normalize_input(text)
        body = json.dumps({"model": self.model, "input": normalized}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.api_base_url}/embeddings",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        last_exc: Exception | None = None
        for _attempt in range(self.retry_count + 1):
            try:
                with urllib.request.urlopen(
                    request,
                    timeout=self.timeout_seconds,
                ) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                embedding = payload["data"][0]["embedding"]
                break
            except (
                TimeoutError,
                urllib.error.URLError,
                json.JSONDecodeError,
                KeyError,
                IndexError,
                TypeError,
            ) as exc:
                last_exc = exc
        else:
            raise AppError(
                code="embedding_provider_request_failed",
                message="Embedding provider request failed.",
                status_code=502,
            ) from last_exc
        if not isinstance(embedding, list) or not all(
            isinstance(value, (int, float)) for value in embedding
        ):
            raise AppError(
                code="embedding_provider_invalid_response",
                message="Embedding provider response did not include a numeric vector.",
                status_code=502,
            )
        if self.dimension and len(embedding) != self.dimension:
            raise AppError(
                code="embedding_provider_invalid_response",
                message="Embedding provider returned an unexpected vector dimension.",
                status_code=502,
            )
        return [float(value) for value in embedding]


def _normalize_input(text: str) -> str:
    normalized = " ".join(text.split())
    if not normalized:
        raise AppError(
            code="embedding_input_empty",
            message="Embedding input text is required.",
            status_code=400,
        )
    if len(normalized) > MAX_EMBEDDING_INPUT_CHARS:
        raise AppError(
            code="embedding_input_too_large",
            message="Embedding input text is too large.",
            status_code=400,
        )
    return normalized


def _tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]{2,}", text.lower())
    return tokens or [hashlib.sha256(text.encode("utf-8")).hexdigest()]


def _semantic_features(token: str) -> list[str]:
    features = [token]
    if len(token) >= 4:
        features.extend(token[index : index + 4] for index in range(len(token) - 3))
    return features


def _feature_index(token: str, dimension: int) -> int:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % dimension


def _normalize_vector(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [round(value / norm, 8) for value in vector]


def embedding_id_for_text(text: str, *, model: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"{model}:{digest}"


def embedding_input_hash(text: str) -> str:
    return hashlib.sha256(_normalize_input(text).encode("utf-8")).hexdigest()


def embedding_metadata_for_text(text: str, *, provider: Any) -> dict[str, Any]:
    return {
        "provider": provider.name,
        "model": provider.model,
        "dim": provider.dimension,
        "version": getattr(provider, "version", provider.model),
        "input_hash": embedding_input_hash(text),
        "provider_config_id": getattr(provider, "provider_config_id", provider.name),
        "vector_source": getattr(provider, "vector_source", "unknown"),
        "semantic": bool(getattr(provider, "semantic", False)),
    }


def build_embedding_provider(settings: Settings | None = None):
    settings = settings or get_settings()
    if settings.embedding_provider in {"local_semantic", "fake_semantic"}:
        return LocalSemanticEmbeddingProvider(
            dimension=settings.embedding_dimension,
            model=settings.embedding_model
            if settings.embedding_model != "local-bow-v1"
            else "local-semantic-v1",
            provider_config_id=settings.embedding_provider_config_id,
        )
    if not settings.enable_real_embedding or settings.embedding_provider in {
        "deterministic",
        "local",
        "local_bow",
    }:
        return LocalVectorEmbeddingProvider(
            dimension=settings.embedding_dimension,
            model=settings.embedding_model,
            provider_config_id=settings.embedding_provider_config_id,
        )
    if settings.embedding_provider not in {"openai_compatible", "generic_http"}:
        raise AppError(
            code="embedding_provider_config_error",
            message="Unsupported embedding provider.",
            status_code=500,
        )
    if (
        not settings.embedding_api_base_url
        or not settings.embedding_api_key
        or not settings.embedding_model
    ):
        raise AppError(
            code="embedding_provider_config_error",
            message="Embedding provider is enabled but missing required configuration.",
            status_code=500,
        )
    return OpenAICompatibleEmbeddingProvider(
        api_base_url=settings.embedding_api_base_url,
        api_key=settings.embedding_api_key,
        model=settings.embedding_model,
        timeout_seconds=settings.llm_timeout_seconds,
        dimension=settings.embedding_dimension,
        provider_config_id=settings.embedding_provider_config_id,
    )
