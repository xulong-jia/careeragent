import json

import pytest

from app.core.config import get_settings
from app.core.errors import AppError
from app.services.resume_ocr_service import build_ocr_provider, detect_resume_layout_signals
from app.services.resume_parser_service import parse_structured_resume


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


def test_deterministic_parser_mode_does_not_require_llm_config(monkeypatch):
    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    parsed = parse_structured_resume(
        "Synthetic Candidate\nSkills: Python, FastAPI\nProjects\nAPI Platform",
        parser_mode="deterministic",
    )

    assert parsed.parser_metadata["parser_mode"] == "deterministic"
    assert parsed.parser_metadata["provider"] == "deterministic"
    assert parsed.parser_metadata["fallback_used"] is False


def test_llm_parser_mode_accepts_schema_valid_provider_output(monkeypatch):
    content = {
        "basic_info": {"name": "Synthetic Candidate"},
        "education": [],
        "projects": [{"name": "Provider Parsed Project"}],
        "experience": [],
        "skills": {"programming": ["Python"]},
        "certificates": [],
        "awards": [],
        "risk_flags": [],
        "parse_confidence": 0.91,
        "evidence": [],
        "warnings": [],
        "parser_metadata": {},
    }

    monkeypatch.setenv("ENABLE_REAL_LLM", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_BASE_URL", "https://provider.example/v1")
    monkeypatch.setenv("LLM_API_KEY", "sk-testsecret123456789")
    monkeypatch.setenv("LLM_MODEL", "synthetic-llm")
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: _FakeResponse(
            {"choices": [{"message": {"content": json.dumps(content)}}]}
        ),
    )

    parsed = parse_structured_resume(
        "Synthetic Candidate\nSkills: Python\nProjects\nProvider Parsed Project",
        parser_mode="llm_parser",
    )

    assert parsed.projects[0]["name"] == "Provider Parsed Project"
    assert parsed.parser_metadata["parser_mode"] == "llm_parser"
    assert parsed.parser_metadata["provider"] == "openai_compatible"
    assert parsed.parser_metadata["model"] == "synthetic-llm"
    assert parsed.parser_metadata["fallback_used"] is False


def test_resume_layout_signals_are_reported_in_metadata_and_warnings():
    raw_text = "\n".join(
        [
            "Synthetic Candidate 候选人",
            "Skills | Python | FastAPI | SQL",
            "项目 | RAG Assistant | 检索增强生成",
            "Education | Synthetic University | Master",
            "Experience | Backend Intern | API contracts",
        ]
    )

    parsed = parse_structured_resume(raw_text, parser_mode="deterministic")
    signals = detect_resume_layout_signals(raw_text)

    assert signals["bilingual_resume"] is True
    assert signals["table_like_resume"] is True
    assert parsed.parser_metadata["layout_signals"]["bilingual_resume"] is True
    assert parsed.parser_metadata["layout_signals"]["table_like_resume"] is True
    assert "bilingual_resume_layout_detected" in parsed.warnings
    assert "table_like_resume_layout_detected" in parsed.warnings
    assert parsed.parser_metadata["ocr_supported"] is False
    assert parsed.parser_metadata["table_resume_foundation"] is True


def test_unsupported_ocr_provider_is_explicit_not_silent():
    provider = build_ocr_provider()

    with pytest.raises(AppError) as exc_info:
        provider.extract_text(b"synthetic image bytes", filename="resume.png")

    assert exc_info.value.code == "resume_ocr_not_configured"
