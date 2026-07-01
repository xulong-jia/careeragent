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

    def __init__(self, *, dimension: int = 384, model: str = "local-bow-v1") -> None:
        if dimension <= 0:
            raise AppError(
                code="embedding_provider_config_error",
                message="Embedding dimension must be greater than zero.",
                status_code=500,
            )
        self.dimension = dimension
        self.model = model
        self.version = "local-bow-v1"

    def embed_text(self, text: str) -> list[float]:
        normalized = _normalize_input(text)
        vector = [0.0] * self.dimension
        for token in _tokenize(normalized):
            index = _feature_index(token, self.dimension)
            vector[index] += 1.0
        return _normalize_vector(vector)


class DeterministicEmbeddingProvider(LocalVectorEmbeddingProvider):
    name = "deterministic"


class OpenAICompatibleEmbeddingProvider:
    name = "openai_compatible"

    def __init__(
        self,
        *,
        api_base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
        dimension: int,
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.dimension = dimension
        self.version = model

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
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
            embedding = payload["data"][0]["embedding"]
        except (TimeoutError, urllib.error.URLError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise AppError(
                code="embedding_provider_request_failed",
                message="Embedding provider request failed.",
                status_code=502,
            ) from exc
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


def build_embedding_provider(settings: Settings | None = None):
    settings = settings or get_settings()
    if not settings.enable_real_embedding or settings.embedding_provider in {
        "deterministic",
        "local",
        "local_bow",
    }:
        return LocalVectorEmbeddingProvider(
            dimension=settings.embedding_dimension,
            model=settings.embedding_model,
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
    )
