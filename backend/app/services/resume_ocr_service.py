from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from app.core.errors import AppError


class ResumeOcrProvider(Protocol):
    name: str

    def extract_text(self, content: bytes, *, filename: str | None = None) -> str:
        ...


@dataclass(frozen=True)
class UnsupportedOcrProvider:
    name: str = "unsupported"

    def extract_text(self, content: bytes, *, filename: str | None = None) -> str:
        del content, filename
        raise AppError(
            code="resume_ocr_not_configured",
            message="Resume OCR provider is not configured.",
            status_code=501,
        )


def build_ocr_provider(mode: str | None = None) -> ResumeOcrProvider:
    normalized = (mode or "unsupported").strip().lower()
    if normalized in {"unsupported", "none", "disabled"}:
        return UnsupportedOcrProvider()
    raise AppError(
        code="resume_ocr_provider_config_error",
        message="Unsupported resume OCR provider.",
        status_code=500,
        details={"provider": normalized},
    )


def detect_resume_layout_signals(raw_text: str) -> dict[str, bool]:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    latin_chars = len(re.findall(r"[A-Za-z]", raw_text))
    cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", raw_text))
    table_like_lines = sum(1 for line in lines if _looks_table_like(line))
    noisy_lines = sum(1 for line in lines if _looks_noisy(line))
    line_count = max(1, len(lines))
    return {
        "bilingual_resume": latin_chars >= 40 and cjk_chars >= 8,
        "table_like_resume": table_like_lines / line_count >= 0.25,
        "noisy_layout": noisy_lines / line_count >= 0.35,
    }


def layout_warnings(raw_text: str) -> list[str]:
    signals = detect_resume_layout_signals(raw_text)
    warnings: list[str] = []
    if signals["bilingual_resume"]:
        warnings.append("bilingual_resume_layout_detected")
    if signals["table_like_resume"]:
        warnings.append("table_like_resume_layout_detected")
    if signals["noisy_layout"]:
        warnings.append("noisy_resume_layout_detected")
    return warnings


def _looks_table_like(line: str) -> bool:
    if "|" in line or "\t" in line:
        return True
    if line.count("  ") >= 2:
        return True
    return bool(re.search(r"\b[A-Za-z ]+:\s+[^:]+:\s+", line))


def _looks_noisy(line: str) -> bool:
    if len(line) < 4:
        return True
    alnum_or_cjk = len(re.findall(r"[A-Za-z0-9\u4e00-\u9fff]", line))
    return (alnum_or_cjk / max(1, len(line))) < 0.45
