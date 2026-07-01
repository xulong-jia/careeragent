from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, TypeVar

from pydantic import BaseModel

from app.ai.validators import validate_structured_output
from app.core.config import Settings, get_settings
from app.core.errors import AppError


T = TypeVar("T", bound=BaseModel)
DEFAULT_RETRY_COUNT = 1


class DeterministicLLMProvider:
    name = "deterministic"

    def generate_structured(
        self,
        *,
        prompt: str,
        schema: type[T],
        fallback: dict[str, Any] | None = None,
        max_output_length: int = 4000,
        temperature: float = 0.0,
    ) -> T:
        del prompt, max_output_length, temperature
        return validate_structured_output(fallback or {}, schema)


class OpenAICompatibleLLMProvider:
    name = "openai_compatible"

    def __init__(
        self,
        *,
        api_base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
        retry_count: int = DEFAULT_RETRY_COUNT,
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.retry_count = retry_count

    def generate_structured(
        self,
        *,
        prompt: str,
        schema: type[T],
        fallback: dict[str, Any] | None = None,
        max_output_length: int = 4000,
        temperature: float = 0.0,
    ) -> T:
        del fallback
        body = json.dumps(
            {
                "model": self.model,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.api_base_url}/chat/completions",
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
                    request, timeout=self.timeout_seconds
                ) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                break
            except (TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
                last_exc = exc
        else:
            raise AppError(
                code="ai_provider_request_failed",
                message="LLM provider request failed.",
                status_code=502,
            ) from last_exc

        content = _extract_openai_content(payload)
        if len(content) > max_output_length:
            raise AppError(
                code="ai_provider_output_too_large",
                message="LLM provider output exceeded the configured limit.",
                status_code=502,
            )
        return validate_structured_output(content, schema)


def _extract_openai_content(payload: dict[str, Any]) -> str:
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AppError(
            code="ai_provider_invalid_response",
            message="LLM provider response did not include structured content.",
            status_code=502,
        ) from exc
    if not isinstance(content, str):
        raise AppError(
            code="ai_provider_invalid_response",
            message="LLM provider content must be a string.",
            status_code=502,
        )
    return content


def build_llm_provider(settings: Settings | None = None):
    settings = settings or get_settings()
    if not settings.enable_real_llm or settings.llm_provider == "deterministic":
        return DeterministicLLMProvider()
    if settings.llm_provider not in {"openai_compatible", "generic_http"}:
        raise AppError(
            code="ai_provider_config_error",
            message="Unsupported LLM provider.",
            status_code=500,
        )
    if not settings.llm_api_base_url or not settings.llm_api_key or not settings.llm_model:
        raise AppError(
            code="ai_provider_config_error",
            message="LLM provider is enabled but missing required configuration.",
            status_code=500,
        )
    return OpenAICompatibleLLMProvider(
        api_base_url=settings.llm_api_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )
