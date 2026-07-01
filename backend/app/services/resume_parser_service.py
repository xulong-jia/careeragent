from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from app.ai.llm_provider import build_llm_provider
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.versioning import PROMPT_VERSION, SCHEMA_VERSION
from app.schemas.resumes import StructuredResume
from app.services.resume_ocr_service import (
    detect_resume_layout_signals,
    layout_warnings,
)


PARSER_METHOD = "deterministic_resume_parser_v2"
RESUME_PARSER_VERSION = "real-resume-parser-foundation-v1"
RESUME_PROMPT_VERSION = "resume-parser-prompt-v2.3"
PARSER_MODES = {"auto", "deterministic", "llm_parser"}

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
URL_RE = re.compile(r"https?://[^\s,;]+|(?:github|linkedin)\.com/[^\s,;]+", re.IGNORECASE)
DATE_RANGE_RE = re.compile(
    r"(?P<start>(?:19|20)\d{2}(?:[./-]\d{1,2})?)\s*"
    r"(?:-|–|—|to|至|到)\s*"
    r"(?P<end>present|current|now|至今|现在|(?:19|20)\d{2}(?:[./-]\d{1,2})?)",
    re.IGNORECASE,
)

SECTION_HEADINGS = {
    "education": {
        "education",
        "education background",
        "academic background",
        "教育经历",
        "教育背景",
        "学历",
    },
    "projects": {
        "projects",
        "project experience",
        "selected projects",
        "项目经历",
        "项目经验",
        "项目",
    },
    "experience": {
        "experience",
        "work experience",
        "professional experience",
        "internship experience",
        "工作经历",
        "实习经历",
        "经历",
    },
    "skills": {
        "skills",
        "technical skills",
        "core skills",
        "技能",
        "专业技能",
        "技术栈",
    },
    "certificates": {
        "certificates",
        "certifications",
        "licenses",
        "证书",
        "认证",
        "资格证书",
    },
    "awards": {
        "awards",
        "honors",
        "honours",
        "获奖",
        "荣誉",
        "奖项",
    },
}

SKILL_CATALOG: dict[str, list[str]] = {
    "programming": ["Python", "TypeScript", "JavaScript", "Java", "Go", "C++"],
    "backend": [
        "FastAPI",
        "Django",
        "Flask",
        "Node.js",
        "Express",
        "Spring Boot",
        "REST",
        "GraphQL",
    ],
    "frontend": ["React", "Vue", "Angular", "HTML", "CSS", "Tailwind"],
    "ai": [
        "LLM",
        "RAG",
        "LangChain",
        "OpenAI",
        "PyTorch",
        "TensorFlow",
        "scikit-learn",
        "Machine Learning",
        "NLP",
        "Embeddings",
    ],
    "database": ["PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis", "SQL"],
    "tools": ["Docker", "Kubernetes", "Git", "AWS", "GCP", "Azure", "Linux", "CI/CD", "GitHub Actions"],
}

DEGREE_KEYWORDS = [
    "bachelor",
    "master",
    "phd",
    "doctor",
    "b.s.",
    "m.s.",
    "本科",
    "学士",
    "硕士",
    "博士",
]

METRIC_RE = re.compile(
    r"(\d+(?:\.\d+)?\s?%|\$\s?\d+|\d+\s?(?:k|m|million|users|用户|人|万|次)|"
    r"accuracy|准确率|revenue|收益|营收|提升|increase|improve|reduced|reduction)",
    re.IGNORECASE,
)
STRONG_CLAIM_RE = re.compile(
    r"(production|launched|上线|生产|million|百万|enterprise|revenue|收益|准确率|"
    r"accuracy|at scale|大规模|expert|精通)",
    re.IGNORECASE,
)


def parse_structured_resume(
    raw_text: str,
    *,
    parser_mode: str = "auto",
) -> StructuredResume:
    normalized_mode = _normalize_parser_mode(parser_mode)
    layout_signals = detect_resume_layout_signals(raw_text)
    fallback = build_deterministic_structured_resume(raw_text)
    if normalized_mode == "deterministic":
        return _with_parser_metadata(
            fallback,
            provider_name="deterministic",
            model=None,
            fallback_used=False,
            fallback_reason=None,
            parser_mode=normalized_mode,
            layout_signals=layout_signals,
        )

    settings = get_settings()
    try:
        provider = build_llm_provider(settings)
    except AppError as exc:
        return _with_parser_metadata(
            fallback,
            provider_name="deterministic",
            model=None,
            fallback_used=True,
            fallback_reason=exc.code,
            parser_mode=normalized_mode,
            layout_signals=layout_signals,
            extra_warnings=["llm_provider_config_failed_fallback"],
        )

    if provider.name == "deterministic":
        return _with_parser_metadata(
            provider.generate_structured(
                prompt=_build_resume_prompt(raw_text),
                schema=StructuredResume,
                fallback=fallback.model_dump(),
            ),
            provider_name=provider.name,
            model=getattr(provider, "model", None),
            fallback_used=True,
            fallback_reason="llm_disabled_or_not_configured",
            parser_mode=normalized_mode,
            layout_signals=layout_signals,
        )

    try:
        parsed = provider.generate_structured(
            prompt=_build_resume_prompt(raw_text),
            schema=StructuredResume,
            fallback=fallback.model_dump(),
            temperature=settings.llm_temperature,
        )
    except AppError as exc:
        return _with_parser_metadata(
            fallback,
            provider_name=provider.name,
            model=getattr(provider, "model", None),
            fallback_used=True,
            fallback_reason=exc.code,
            parser_mode=normalized_mode,
            layout_signals=layout_signals,
            extra_warnings=["llm_parser_failed_fallback"],
        )
    return _with_parser_metadata(
        _normalize_structured_resume(parsed),
        provider_name=provider.name,
        model=getattr(provider, "model", None),
        fallback_used=False,
        fallback_reason=None,
        parser_mode=normalized_mode,
        layout_signals=layout_signals,
    )


def build_deterministic_structured_resume(raw_text: str) -> StructuredResume:
    sections = _split_sections(raw_text)
    skills, skill_evidence, skill_warnings = _parse_skills(raw_text, sections)
    education = _parse_education(sections.get("education", []))
    projects = _parse_projects(sections.get("projects", []))
    experience = _parse_experience(sections.get("experience", []))
    certificates = _parse_named_items(sections.get("certificates", []))
    awards = _parse_named_items(sections.get("awards", []))
    warnings = _resume_warnings(raw_text, sections, skills)
    warnings.extend(layout_warnings(raw_text))
    warnings.extend(skill_warnings)
    evidence = _section_evidence(sections)
    evidence.extend(skill_evidence)
    evidence.extend(_record_evidence("education", education))
    evidence.extend(_record_evidence("projects", projects))
    evidence.extend(_record_evidence("experience", experience))
    warnings = _dedupe(warnings)
    risk_flags = _parser_risk_flags(
        projects=projects,
        experience=experience,
        education=education,
        skills=skills,
        warnings=warnings,
    )
    parse_confidence = _resume_confidence(
        sections=sections,
        skills=skills,
        projects=projects,
        education=education,
        evidence=evidence,
        warnings=warnings,
    )
    return StructuredResume(
        basic_info=_parse_basic_info(raw_text, sections.get("summary", [])),
        education=education,
        projects=projects,
        experience=experience,
        skills=skills,
        certificates=certificates,
        awards=awards,
        risk_flags=risk_flags,
        parse_confidence=parse_confidence,
        evidence=evidence,
        warnings=warnings,
        parser_metadata=_parser_metadata(
            provider_name="deterministic",
            model=None,
            fallback_used=False,
            fallback_reason=None,
            parser_mode="deterministic",
            layout_signals=detect_resume_layout_signals(raw_text),
        ),
    )


def _normalize_parser_mode(parser_mode: str | None) -> str:
    normalized = (parser_mode or "auto").strip().lower()
    if normalized not in PARSER_MODES:
        raise AppError(
            code="resume_parser_mode_invalid",
            message="Unsupported resume parser mode.",
            status_code=400,
            details={"parser_mode": parser_mode},
        )
    return normalized


def _split_sections(raw_text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"summary": []}
    current = "summary"
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        heading = _section_key_for_line(line)
        if heading:
            current = heading
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


def _section_key_for_line(line: str) -> str | None:
    normalized = _normalize_heading(line)
    for key, headings in SECTION_HEADINGS.items():
        if normalized in headings:
            return key
    return None


def _normalize_heading(line: str) -> str:
    cleaned = re.sub(r"^[#>\-\*\d.\s]+", "", line).strip()
    cleaned = cleaned.rstrip(":：").strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _strip_marker(line: str) -> str:
    return re.sub(r"^[#>\-\*\u2022\d.\s]+", "", line).strip()


def _parse_basic_info(raw_text: str, summary_lines: list[str]) -> dict[str, object]:
    email_match = EMAIL_RE.search(raw_text)
    phone_match = PHONE_RE.search(raw_text)
    links = sorted({match.rstrip(").]") for match in URL_RE.findall(raw_text)})
    name = _parse_name(summary_lines)
    location = _parse_labeled_value(
        raw_text.splitlines(), ["location", "city", "地点", "城市", "所在地"]
    )
    return {
        "name": name,
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(0).strip() if phone_match else None,
        "location": location,
        "links": links,
    }


def _parse_name(summary_lines: list[str]) -> str | None:
    for line in summary_lines[:5]:
        candidate = _strip_marker(line)
        lowered = candidate.lower()
        if not candidate or any(token in lowered for token in ["resume", "cv", "@", "http"]):
            continue
        if PHONE_RE.search(candidate):
            continue
        if 1 <= len(candidate.split()) <= 5 and len(candidate) <= 80:
            return candidate
    return None


def _parse_labeled_value(lines: Iterable[str], labels: list[str]) -> str | None:
    for line in lines:
        value = _line_value_for_labels(line, labels)
        if value:
            return value
    return None


def _line_value_for_labels(line: str, labels: list[str]) -> str | None:
    clean = _strip_marker(line)
    lower = clean.lower()
    for label in labels:
        label_lower = label.lower()
        for separator in (":", "："):
            prefix = f"{label_lower}{separator}"
            if lower.startswith(prefix):
                return clean[len(prefix) :].strip() or None
    return None


def _build_resume_prompt(raw_text: str) -> str:
    return "\n".join(
        [
            "Return one JSON object matching the StructuredResume schema.",
            "Do not guess missing fields; use null or empty arrays for uncertainty.",
            "Separate projects, internships/work experience, education, skills, certificates, and awards.",
            f"Prompt version: {RESUME_PROMPT_VERSION}",
            "Resume:",
            raw_text,
        ]
    )


def _with_parser_metadata(
    resume: StructuredResume,
    *,
    provider_name: str,
    model: str | None,
    fallback_used: bool,
    fallback_reason: str | None,
    parser_mode: str,
    layout_signals: dict[str, bool],
    extra_warnings: list[str] | None = None,
) -> StructuredResume:
    warnings = _dedupe([*resume.warnings, *(extra_warnings or [])])
    return resume.model_copy(
        update={
            "warnings": warnings,
            "parser_metadata": _parser_metadata(
                provider_name=provider_name,
                model=model,
                fallback_used=fallback_used,
                fallback_reason=fallback_reason,
                parser_mode=parser_mode,
                layout_signals=layout_signals,
            ),
        }
    )


def _parser_metadata(
    *,
    provider_name: str,
    model: str | None,
    fallback_used: bool,
    fallback_reason: str | None,
    parser_mode: str,
    layout_signals: dict[str, bool],
) -> dict[str, object]:
    return {
        "parser_version": RESUME_PARSER_VERSION,
        "prompt_version": RESUME_PROMPT_VERSION,
        "parser_mode": parser_mode,
        "provider": provider_name,
        "model": model,
        "schema_version": SCHEMA_VERSION,
        "base_prompt_version": PROMPT_VERSION,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "ocr_supported": False,
        "ocr_provider": None,
        "table_resume_foundation": True,
        "bilingual_resume_foundation": True,
        "layout_signals": dict(layout_signals),
        "foundation_only": True,
    }


def _normalize_structured_resume(resume: StructuredResume) -> StructuredResume:
    skills = {category: _dedupe(resume.skills.get(category, [])) for category in SKILL_CATALOG}
    warnings = _dedupe(resume.warnings)
    return resume.model_copy(update={"skills": skills, "warnings": warnings})


def _parse_skills(
    raw_text: str, sections: dict[str, list[str]]
) -> tuple[dict[str, list[str]], list[dict[str, object]], list[str]]:
    skill_lines = sections.get("skills", [])
    source_text = "\n".join(skill_lines) if skill_lines else raw_text
    source_lines = skill_lines if skill_lines else raw_text.splitlines()
    warnings = [] if skill_lines else ["skills_inferred_without_skill_section"]
    skills: dict[str, list[str]] = {}
    evidence: list[dict[str, object]] = []
    for category, candidates in SKILL_CATALOG.items():
        found = [skill for skill in candidates if _contains_skill(source_text, skill)]
        skills[category] = found
        for skill in found:
            evidence.append(
                _evidence_item(
                    f"skills.{category}",
                    skill,
                    _first_line_containing(source_lines, skill) or skill,
                    0.78 if skill_lines else 0.55,
                )
            )
    return skills, evidence, warnings


def _contains_skill(raw_text: str, skill: str) -> bool:
    lowered = raw_text.lower()
    skill_lower = skill.lower()
    if skill_lower in {"c++", "node.js", "ci/cd", "github actions", "scikit-learn"}:
        return skill_lower in lowered
    return re.search(rf"\b{re.escape(skill_lower)}\b", lowered) is not None


def _parse_education(lines: list[str]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for line in _meaningful_lines(lines):
        start_date, end_date = _parse_period(line)
        clean = _strip_marker(line)
        segments = _split_segments(clean)
        degree = _first_segment_matching(segments, DEGREE_KEYWORDS)
        courses = _parse_list_value(clean, ["courses", "coursework", "核心课程", "课程"])
        major = _parse_labeled_value([clean], ["major", "专业"])
        school = _first_school_segment(segments, degree, major, courses)
        if not any([school, degree, major, start_date, end_date, courses]):
            continue
        records.append(
            {
                "school": school,
                "degree": degree,
                "major": major,
                "start_date": start_date,
                "end_date": end_date,
                "courses": courses,
                "raw_text": clean,
            }
        )
    return records


def _first_school_segment(
    segments: list[str],
    degree: str | None,
    major: str | None,
    courses: list[str],
) -> str | None:
    course_set = {course.lower() for course in courses}
    for segment in segments:
        lowered = segment.lower()
        if segment == degree or segment == major:
            continue
        if lowered in course_set or "course" in lowered or "课程" in segment:
            continue
        if DATE_RANGE_RE.search(segment):
            continue
        return segment
    return None


def _parse_projects(lines: list[str]) -> list[dict[str, object]]:
    return [_parse_project_block(block) for block in _split_blocks(lines) if block]


def _parse_project_block(block: list[str]) -> dict[str, object]:
    first_line = _strip_marker(block[0]) if block else ""
    name = _parse_labeled_value(block, ["name", "project", "项目名称"]) or first_line or None
    role = _parse_labeled_value(block, ["role", "角色"])
    period = _parse_labeled_value(block, ["period", "date", "time", "时间", "周期"])
    start_date, end_date = _parse_period(period or "\n".join(block))
    tech_stack = _parse_list_value("\n".join(block), ["tech", "tech stack", "技术栈", "技术"])
    responsibilities = _parse_list_value(
        "\n".join(block), ["responsibilities", "duties", "负责", "职责"]
    )
    results = _parse_list_value("\n".join(block), ["results", "impact", "outcome", "成果", "结果"])
    evidence = _parse_list_value("\n".join(block), ["evidence", "proof", "证据", "佐证"])
    background = _parse_labeled_value(block, ["background", "context", "背景"])
    return {
        "name": name,
        "role": role,
        "period": period,
        "start_date": start_date,
        "end_date": end_date,
        "background": background,
        "tech_stack": tech_stack,
        "responsibilities": responsibilities,
        "results": results,
        "evidence": evidence,
        "risk_flags": [],
        "raw_text": "\n".join(_strip_marker(line) for line in block),
    }


def _parse_experience(lines: list[str]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for block in _split_blocks(lines):
        first_line = _strip_marker(block[0]) if block else ""
        company = _parse_labeled_value(block, ["company", "公司"])
        role = _parse_labeled_value(block, ["role", "title", "岗位", "职位"])
        period = _parse_labeled_value(block, ["period", "date", "time", "时间", "周期"])
        start_date, end_date = _parse_period(period or "\n".join(block))
        responsibilities = _parse_list_value(
            "\n".join(block), ["responsibilities", "duties", "负责", "职责"]
        )
        results = _parse_list_value("\n".join(block), ["results", "impact", "成果", "结果"])
        if any([company, role, start_date, end_date, responsibilities, results]):
            records.append(
                {
                    "company": company or first_line or None,
                    "role": role,
                    "period": period,
                    "start_date": start_date,
                    "end_date": end_date,
                    "responsibilities": responsibilities,
                    "results": results,
                    "raw_text": "\n".join(_strip_marker(line) for line in block),
                }
            )
    return records


def _parse_named_items(lines: list[str]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for line in _meaningful_lines(lines):
        clean = _strip_marker(line)
        start_date, end_date = _parse_period(clean)
        records.append(
            {
                "name": clean,
                "start_date": start_date,
                "end_date": end_date,
                "raw_text": clean,
            }
        )
    return records


def _split_blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in _meaningful_lines(lines):
        if current and _looks_like_block_title(line):
            blocks.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append(current)
    return blocks


def _looks_like_block_title(line: str) -> bool:
    clean = _strip_marker(line)
    if line.lstrip().startswith("#"):
        return True
    if _line_value_for_labels(clean, ["name", "project", "项目名称"]):
        return True
    if ":" in clean or "：" in clean:
        return False
    return 1 <= len(clean.split()) <= 8 and len(clean) <= 100


def _meaningful_lines(lines: list[str]) -> list[str]:
    return [line for line in (item.strip() for item in lines) if line]


def _parse_period(text: str | None) -> tuple[str | None, str | None]:
    if not text:
        return None, None
    match = DATE_RANGE_RE.search(text)
    if not match:
        return None, None
    return _normalize_date(match.group("start")), _normalize_date(match.group("end"))


def _normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    lowered = value.strip().lower()
    if lowered in {"present", "current", "now", "至今", "现在"}:
        return "present"
    return lowered.replace("/", "-").replace(".", "-")


def _parse_list_value(text: str, labels: list[str]) -> list[str]:
    for line in text.splitlines():
        value = _line_value_for_labels(line, labels)
        if value:
            return _split_list(value)
    return []


def _split_list(value: str) -> list[str]:
    items = re.split(r"[,;/，；、]|\s+\|\s+", value)
    return [item.strip(" .") for item in items if item.strip(" .")]


def _split_segments(value: str) -> list[str]:
    segments = re.split(r"\s+\|\s+|[,，；;]", value)
    return [segment.strip() for segment in segments if segment.strip()]


def _first_segment_matching(segments: list[str], keywords: list[str]) -> str | None:
    for segment in segments:
        lowered = segment.lower()
        if any(keyword in lowered for keyword in keywords):
            return segment
    return None


def _resume_warnings(
    raw_text: str, sections: dict[str, list[str]], skills: dict[str, list[str]]
) -> list[str]:
    warnings: list[str] = []
    text = raw_text.strip()
    recognized_sections = [key for key in SECTION_HEADINGS if sections.get(key)]
    if len(text) < 80:
        warnings.append("resume_text_short_low_confidence")
    if not recognized_sections:
        warnings.append("no_recognized_resume_sections")
    if not any(skills.values()):
        warnings.append("no_skills_detected")
    if sections.get("experience") and any(
        "project" in line.lower() or "项目" in line for line in sections["experience"]
    ):
        warnings.append("ambiguous_section_project_inside_experience")
    if sections.get("projects") and any(
        "company:" in line.lower() or "公司" in line for line in sections["projects"]
    ):
        warnings.append("ambiguous_section_experience_inside_project")
    if len(re.findall(r"[A-Za-z\u4e00-\u9fff]", text)) < 20:
        warnings.append("invalid_or_sparse_resume_text")
    return warnings


def _section_evidence(sections: dict[str, list[str]]) -> list[dict[str, object]]:
    evidence: list[dict[str, object]] = []
    for field in ("education", "projects", "experience", "skills", "certificates", "awards"):
        lines = sections.get(field, [])
        if lines:
            evidence.append(_evidence_item(field, "section_present", lines[0], 0.74))
    return evidence


def _record_evidence(
    field: str, records: list[dict[str, object]]
) -> list[dict[str, object]]:
    evidence: list[dict[str, object]] = []
    for record in records[:5]:
        value = record.get("name") or record.get("school") or record.get("company")
        raw_text = record.get("raw_text") or value
        if value and raw_text:
            evidence.append(_evidence_item(field, str(value), str(raw_text), 0.76))
    return evidence


def _parser_risk_flags(
    *,
    projects: list[dict[str, object]],
    experience: list[dict[str, object]],
    education: list[dict[str, object]],
    skills: dict[str, list[str]],
    warnings: list[str],
) -> list[dict[str, object]]:
    flags: list[dict[str, object]] = []
    if any("low_confidence" in warning for warning in warnings):
        flags.append(
            _risk_flag(
                "parse_low_confidence",
                "medium",
                "Parser confidence is low; manual confirmation is required.",
                "structured_resume",
                ", ".join(warnings),
            )
        )
    if any("ambiguous_section" in warning for warning in warnings):
        flags.append(
            _risk_flag(
                "ambiguous_section",
                "medium",
                "Resume section boundaries are ambiguous.",
                "structured_resume",
                ", ".join(warnings),
            )
        )

    declared_skills = {
        str(skill).strip().lower()
        for values in skills.values()
        for skill in values
        if str(skill).strip()
    }
    for collection_name, records in (
        ("education", education),
        ("projects", projects),
        ("experience", experience),
    ):
        for index, record in enumerate(records):
            start_date, end_date = record.get("start_date"), record.get("end_date")
            if _date_key(start_date) and _date_key(end_date) and _date_key(start_date) > _date_key(end_date):
                flags.append(
                    _risk_flag(
                        "timeline_conflict",
                        "high",
                        "Start date is later than end date.",
                        f"{collection_name}[{index}]",
                        f"{start_date} > {end_date}",
                    )
                )

    for index, project in enumerate(projects):
        location = f"projects[{index}]"
        for skill in _as_list(project.get("tech_stack")):
            normalized = str(skill).strip().lower()
            if normalized and normalized not in declared_skills:
                flags.append(
                    _risk_flag(
                        "fabricated_skill",
                        "medium",
                        "Project tech stack contains a skill not declared in skills.",
                        f"{location}.tech_stack",
                        str(skill),
                    )
                )
        claim_text = " ".join(
            str(item)
            for key in ("results", "responsibilities", "background")
            for item in _as_list(project.get(key))
        )
        has_evidence = any(str(item).strip() for item in _as_list(project.get("evidence")))
        if claim_text.strip() and not has_evidence:
            if METRIC_RE.search(claim_text):
                flags.append(
                    _risk_flag(
                        "unsupported_metric",
                        "high",
                        "Metric or quantified outcome has no supporting evidence.",
                        location,
                        claim_text,
                    )
                )
            if STRONG_CLAIM_RE.search(claim_text):
                flags.append(
                    _risk_flag(
                        "overclaim",
                        "medium",
                        "Strong production, scale, revenue, or expertise claim has no evidence.",
                        location,
                        claim_text,
                    )
                )
            if _as_list(project.get("results")):
                flags.append(
                    _risk_flag(
                        "missing_evidence",
                        "medium",
                        "Result claim has no supporting evidence.",
                        location,
                        claim_text,
                    )
                )
    return _dedupe_risk_flags(flags)


def _resume_confidence(
    *,
    sections: dict[str, list[str]],
    skills: dict[str, list[str]],
    projects: list[dict[str, object]],
    education: list[dict[str, object]],
    evidence: list[dict[str, object]],
    warnings: list[str],
) -> float:
    score = 0.4
    if sections.get("skills"):
        score += 0.14
    if any(skills.values()):
        score += 0.12
    if projects:
        score += 0.1
    if education:
        score += 0.1
    if evidence:
        score += 0.08
    score -= min(0.28, len(warnings) * 0.06)
    return round(max(0.05, min(0.95, score)), 2)


def _risk_flag(
    flag_type: str,
    severity: str,
    message: str,
    location: str,
    evidence: str,
) -> dict[str, object]:
    return {
        "type": flag_type,
        "severity": severity,
        "message": message,
        "location": location,
        "evidence": evidence[:500],
    }


def _dedupe_risk_flags(flags: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[tuple[str, str, str]] = set()
    result: list[dict[str, object]] = []
    for flag in flags:
        key = (
            str(flag.get("type")),
            str(flag.get("location")),
            str(flag.get("evidence")),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(flag)
    return result


def _date_key(value: Any) -> tuple[int, int] | None:
    if not isinstance(value, str):
        return None
    lowered = value.strip().lower()
    if lowered in {"present", "current", "now", "至今", "现在", ""}:
        return None
    match = re.search(r"(?P<year>(?:19|20)\d{2})(?:[-/.](?P<month>\d{1,2}))?", lowered)
    if not match:
        return None
    return int(match.group("year")), int(match.group("month") or 1)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [value]


def _first_line_containing(lines: Iterable[str], value: str) -> str | None:
    normalized = value.lower()
    for line in lines:
        if normalized in str(line).lower():
            return str(line).strip()
    return None


def _evidence_item(
    field: str, value: str, evidence_text: str, confidence: float
) -> dict[str, object]:
    return {
        "field": field,
        "value": value,
        "evidence_text": evidence_text[:500],
        "confidence": confidence,
    }


def _dedupe(values: Iterable[Any]) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for value in values:
        key = str(value).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result
