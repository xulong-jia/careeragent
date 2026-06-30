from __future__ import annotations

import json
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.errors import AppError


T = TypeVar("T", bound=BaseModel)


def parse_json_payload(value: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise AppError(
            code="ai_schema_validation_failed",
            message="AI provider returned invalid JSON.",
            status_code=502,
        ) from exc
    if not isinstance(parsed, dict):
        raise AppError(
            code="ai_schema_validation_failed",
            message="AI provider JSON output must be an object.",
            status_code=502,
        )
    return parsed


def validate_structured_output(value: str | dict[str, Any], schema: type[T]) -> T:
    try:
        return schema.model_validate(parse_json_payload(value))
    except ValidationError as exc:
        raise AppError(
            code="ai_schema_validation_failed",
            message="AI provider output failed schema validation.",
            status_code=502,
        ) from exc
