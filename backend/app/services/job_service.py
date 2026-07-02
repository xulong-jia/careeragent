from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.ai.llm_provider import build_llm_provider
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.versioning import PROMPT_VERSION, SCHEMA_VERSION
from app.repositories import job_repository
from app.schemas.jobs import JobCreateRequest, JobProfile, JobRecord


MIN_JD_TEXT_LENGTH = 20
JD_PARSER_VERSION = "real-jd-parser-foundation-v1"
JD_PROMPT_VERSION = "jd-parser-prompt-v2.3"

REQUIRED_CUES = (
    "must",
    "required",
    "require",
    "need",
    "needs",
    "minimum",
    "responsible for",
    "responsibilities include",
    "build",
    "own",
    "maintain",
    "deliver",
    "create",
    "develop",
    "design",
    "implement",
    "operate",
    "support",
    "必备",
    "要求",
    "熟练",
    "精通",
    "负责",
)
PREFERRED_CUES = (
    "preferred",
    "nice to have",
    "bonus",
    "plus",
    "加分",
    "优先",
    "熟悉更佳",
)
ACTION_CUES = (
    "build",
    "own",
    "maintain",
    "deliver",
    "create",
    "develop",
    "design",
    "implement",
    "operate",
    "support",
    "review",
    "responsibilities include",
    "负责",
)
SKILL_PATTERNS = {
    "Python": (r"\bpython\b",),
    "FastAPI": (r"\bfastapi\b",),
    "SQL": (r"\bsql\b",),
    "PostgreSQL": (r"\bpostgresql\b",),
    "TypeScript": (r"\btypescript\b",),
    "JavaScript": (r"\bjavascript\b",),
    "React": (r"\breact\b",),
    "Docker": (r"\bdocker\b",),
    "Kubernetes": (r"\bkubernetes\b", r"\bk8s\b"),
    "RAG": (r"\brag\b",),
    "LLM": (r"\bllm\b", r"\blarge language model"),
    "OpenAI": (r"\bopenai\b",),
    "Vector Search": (r"\bvector search\b", r"\bsemantic search\b"),
    "Embeddings": (r"\bembedding",),
    "Airflow": (r"\bairflow\b",),
    "Spark": (r"\bspark\b",),
    "dbt": (r"\bdbt\b",),
    "PyTorch": (r"\bpytorch\b",),
    "OpenCV": (r"\bopencv\b",),
    "Computer Vision": (r"\bcomputer vision\b", r"\bobject detection\b"),
    "Power BI": (r"\bpower bi\b",),
    "Tableau": (r"\btableau\b",),
}
ROLE_CATEGORIES = (
    "LLM Application Engineer",
    "Python Backend Developer",
    "AI Application Engineer",
    "Frontend / Fullstack Developer",
    "Data Analyst / Data Engineer",
    "Data Platform Engineer",
    "Computer Vision Engineer",
    "Bank IT Graduate Program",
    "Enterprise Digitalization Role",
    "Other",
)


def validate_job_description(raw_text: str) -> None:
    if len(raw_text.strip()) < MIN_JD_TEXT_LENGTH:
        raise AppError(
            code="job_description_too_short",
            message="JD raw_text is too short for parser foundation extraction.",
            status_code=400,
            details={"min_length": MIN_JD_TEXT_LENGTH},
        )


def parse_job_profile(jd_id: str, payload: JobCreateRequest) -> JobProfile:
    fallback = build_deterministic_job_profile(jd_id, payload)
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
            extra_warnings=["llm_provider_config_failed_fallback"],
        )

    if provider.name == "deterministic":
        return _with_parser_metadata(
            provider.generate_structured(
                prompt=_build_jd_prompt(payload),
                schema=JobProfile,
                fallback=fallback.model_dump(),
            ),
            provider_name=provider.name,
            model=getattr(provider, "model", None),
            fallback_used=True,
            fallback_reason="llm_disabled_or_not_configured",
        )

    try:
        parsed = provider.generate_structured(
            prompt=_build_jd_prompt(payload),
            schema=JobProfile,
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
            extra_warnings=["llm_parser_failed_fallback"],
        )
    return _with_parser_metadata(
        _normalize_profile(parsed, payload),
        provider_name=provider.name,
        model=getattr(provider, "model", None),
        fallback_used=False,
        fallback_reason=None,
    )


def build_deterministic_job_profile(jd_id: str, payload: JobCreateRequest) -> JobProfile:
    statements = _split_statements(payload.raw_text)
    required_skills, preferred_skills, evidence = _extract_skills_with_evidence(
        statements
    )
    responsibilities = _extract_responsibilities(statements)
    business_scenarios = _extract_business_scenarios(statements)
    role_category, role_evidence = infer_role_category(payload.job_title, payload.raw_text)
    hidden_requirements = _extract_hidden_requirements(statements, role_category)
    warnings = _job_warnings(payload.raw_text, required_skills, responsibilities)
    if _has_backend_mobile_conflict(payload.job_title, payload.raw_text):
        role_category = "Other"
        warnings.append("role_category_ambiguous_backend_mobile")
        role_evidence.append(
            _evidence_item(
                "role_category",
                "ambiguous_backend_mobile",
                payload.job_title,
                0.52,
            )
        )
    evidence.extend(role_evidence)
    evidence.extend(
        _evidence_item(
            "responsibilities",
            responsibility,
            responsibility,
            0.78,
        )
        for responsibility in responsibilities[:3]
    )
    parse_confidence = _job_confidence(
        role_category=role_category,
        required_skills=required_skills,
        responsibilities=responsibilities,
        evidence=evidence,
        warnings=warnings,
    )
    return JobProfile(
        job_profile_id=f"profile_{jd_id}",
        job_title=payload.job_title,
        company=payload.company,
        location=payload.location,
        role_category=role_category,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        responsibilities=responsibilities,
        business_scenarios=business_scenarios,
        hidden_requirements=hidden_requirements,
        interview_focus=_interview_focus(role_category, required_skills, hidden_requirements),
        risk_level=_risk_level(parse_confidence, warnings),
        summary=_summary(role_category, required_skills, preferred_skills, warnings),
        parse_confidence=parse_confidence,
        evidence=evidence,
        warnings=warnings,
        parser_metadata=_parser_metadata(
            provider_name="deterministic",
            model=None,
            fallback_used=False,
            fallback_reason=None,
        ),
    )


def create_job(db: Session, payload: JobCreateRequest) -> JobRecord:
    validate_job_description(payload.raw_text)
    profile = parse_job_profile("pending", payload)
    return job_repository.create_job_with_profile(db, payload=payload, profile=profile)


def list_jobs(db: Session) -> list[JobRecord]:
    return job_repository.list_jobs(db)


def get_job(db: Session, jd_id: str) -> JobRecord:
    return job_repository.get_job(db, jd_id)


def archive_job(db: Session, jd_id: str) -> dict[str, object]:
    return job_repository.archive_job(db, jd_id)


def _build_jd_prompt(payload: JobCreateRequest) -> str:
    return "\n".join(
        [
            "Return one JSON object matching the JobProfile schema.",
            "Do not guess missing fields; use null or empty arrays for uncertainty.",
            f"Prompt version: {JD_PROMPT_VERSION}",
            f"Company: {payload.company}",
            f"Job title: {payload.job_title}",
            f"Location: {payload.location or ''}",
            "JD:",
            payload.raw_text,
        ]
    )


def _with_parser_metadata(
    profile: JobProfile,
    *,
    provider_name: str,
    model: str | None,
    fallback_used: bool,
    fallback_reason: str | None,
    extra_warnings: list[str] | None = None,
) -> JobProfile:
    warnings = _dedupe([*profile.warnings, *(extra_warnings or [])])
    metadata = _parser_metadata(
        provider_name=provider_name,
        model=model,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
    )
    return profile.model_copy(update={"warnings": warnings, "parser_metadata": metadata})


def _parser_metadata(
    *,
    provider_name: str,
    model: str | None,
    fallback_used: bool,
    fallback_reason: str | None,
) -> dict[str, object]:
    return {
        "parser_version": JD_PARSER_VERSION,
        "prompt_version": JD_PROMPT_VERSION,
        "provider": provider_name,
        "model": model,
        "schema_version": SCHEMA_VERSION,
        "base_prompt_version": PROMPT_VERSION,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "foundation_only": True,
    }


def _normalize_profile(profile: JobProfile, payload: JobCreateRequest) -> JobProfile:
    return profile.model_copy(
        update={
            "job_title": payload.job_title,
            "company": payload.company,
            "location": payload.location,
            "required_skills": _dedupe(profile.required_skills),
            "preferred_skills": _dedupe(profile.preferred_skills),
            "warnings": _dedupe(profile.warnings),
        }
    )


def _split_statements(raw_text: str) -> list[str]:
    parts = re.split(r"[\n]+|(?<=[.!?。；;])\s+", raw_text)
    return [part.strip(" \t-•*.;。；") for part in parts if part.strip(" \t-•*.;。；")]


def _extract_skills_with_evidence(
    statements: list[str],
) -> tuple[list[str], list[str], list[dict[str, object]]]:
    required: list[str] = []
    preferred: list[str] = []
    evidence: list[dict[str, object]] = []
    for statement in statements:
        skills = _skills_in_text(statement)
        if not skills:
            continue
        lower = statement.lower()
        bucket = (
            "preferred"
            if _has_any(lower, PREFERRED_CUES)
            else "required"
            if _has_any(lower, REQUIRED_CUES)
            else None
        )
        if bucket is None:
            continue
        for skill in skills:
            target = preferred if bucket == "preferred" else required
            target.append(skill)
            evidence.append(
                _evidence_item(
                    f"{bucket}_skills",
                    skill,
                    statement,
                    0.82 if bucket == "required" else 0.76,
                )
            )
    required = _dedupe(required)
    preferred = [skill for skill in _dedupe(preferred) if skill not in set(required)]
    return required, preferred, evidence


def _skills_in_text(text: str) -> list[str]:
    matches: list[str] = []
    lowered = text.lower()
    for skill, patterns in SKILL_PATTERNS.items():
        if any(re.search(pattern, lowered, re.IGNORECASE) for pattern in patterns):
            matches.append(skill)
    return matches


def infer_role_category(
    job_title: str, raw_text: str
) -> tuple[str, list[dict[str, object]]]:
    title = job_title.lower()
    combined = f"{job_title} {raw_text}".lower()
    category = "Other"
    evidence_text = job_title
    if _has_role_term(combined, ("bank", "graduate program", "rotation", "regulatory")):
        category = "Bank IT Graduate Program"
    elif _has_role_term(combined, ("computer vision", "opencv", "object detection", "image")):
        category = "Computer Vision Engineer"
    elif _has_role_term(title, ("data analyst",)):
        category = "Data Analyst / Data Engineer"
    elif _has_role_term(title, ("data platform",)):
        category = "Data Platform Engineer"
    elif _has_role_term(title, ("frontend", "fullstack")):
        category = "Frontend / Fullstack Developer"
    elif _has_role_term(title, ("backend", "api developer")):
        category = "Python Backend Developer"
    elif "llm application" in combined:
        category = "LLM Application Engineer"
    elif _has_any(
        combined,
        ("data platform", "data pipeline", "data quality", "analytics users", "airflow", "spark", "dbt"),
    ):
        category = "Data Platform Engineer"
    elif _has_role_term(combined, ("rag", "llm", "openai", "prompt", "vector search")):
        category = "AI Application Engineer"
    elif _has_role_term(combined, ("frontend", "fullstack", "react", "typescript", "user interface")):
        category = "Frontend / Fullstack Developer"
    elif _has_role_term(combined, ("data analyst", "data engineer", "reporting", "power bi", "tableau")):
        category = "Data Analyst / Data Engineer"
    elif _has_role_term(combined, ("enterprise digital", "digital transformation", "crm", "erp", "sap")):
        category = "Enterprise Digitalization Role"
    elif _has_role_term(combined, ("backend", "fastapi", "api developer", "python service")):
        category = "Python Backend Developer"

    for statement in _split_statements(raw_text):
        if category.lower().split("/")[0].strip() in statement.lower():
            evidence_text = statement
            break
        if category != "Other" and any(
            token in statement.lower() for token in category.lower().split()
        ):
            evidence_text = statement
            break
    return category, [_evidence_item("role_category", category, evidence_text, 0.78)]


def _extract_responsibilities(statements: list[str]) -> list[str]:
    responsibilities = [
        statement
        for statement in statements
        if _has_any(statement.lower(), ACTION_CUES)
        and not _has_any(statement.lower(), PREFERRED_CUES)
    ]
    return _dedupe(responsibilities[:5])


def _extract_business_scenarios(statements: list[str]) -> list[str]:
    scenario_cues = (
        "users",
        "teams",
        "workflow",
        "platform",
        "analytics",
        "operations",
        "candidate",
        "student",
        "policy",
        "bank",
        "enterprise",
        "客户",
        "业务",
    )
    return _dedupe(
        statement for statement in statements if _has_any(statement.lower(), scenario_cues)
    )[:5]


def _extract_hidden_requirements(
    statements: list[str], role_category: str
) -> list[dict[str, object]]:
    checks = [
        (
            "Production API experience",
            ("production", "reliability", "monitoring", "deployment", "api reliability"),
        ),
        (
            "Evidence-grounded AI evaluation",
            ("rag", "llm", "citation", "grounded", "prompt", "vector search"),
        ),
        (
            "Data quality ownership",
            ("data quality", "pipeline", "analytics", "warehouse", "data workflow"),
        ),
        (
            "Enterprise stakeholder communication",
            ("bank", "enterprise", "stakeholder", "regulatory", "rotation"),
        ),
    ]
    hidden: list[dict[str, object]] = []
    for requirement, cues in checks:
        evidence = next(
            (statement for statement in statements if _has_any(statement.lower(), cues)),
            None,
        )
        if evidence:
            hidden.append(
                {"requirement": requirement, "evidence": evidence, "confidence": 0.72}
            )
    if role_category == "Computer Vision Engineer" and not hidden:
        hidden.append(
            {
                "requirement": "Model evaluation and data quality discipline",
                "evidence": "Computer vision role category was inferred from JD text.",
                "confidence": 0.62,
            }
        )
    return hidden


def _interview_focus(
    role_category: str, required_skills: list[str], hidden_requirements: list[dict[str, object]]
) -> list[str]:
    focus = [f"Explain evidence for {skill} in a real project." for skill in required_skills[:3]]
    focus.extend(
        f"Discuss {item['requirement']} with concrete tradeoffs."
        for item in hidden_requirements[:2]
        if item.get("requirement")
    )
    if not focus:
        focus.append(f"Clarify role fit for {role_category} with verifiable evidence.")
    return focus


def _job_warnings(
    raw_text: str, required_skills: list[str], responsibilities: list[str]
) -> list[str]:
    warnings: list[str] = []
    text = raw_text.strip()
    if len(text) < 80:
        warnings.append("job_description_short_low_confidence")
    if len(text) > 12000:
        warnings.append("job_description_very_long_review_required")
    if _looks_duplicate(text):
        warnings.append("duplicate_jd_text_review_required")
    if not required_skills:
        warnings.append("no_required_skills_detected")
    if not responsibilities:
        warnings.append("no_responsibilities_detected")
    if len(re.findall(r"[A-Za-z\u4e00-\u9fff]", text)) < 20:
        warnings.append("invalid_or_sparse_jd_text")
    return warnings


def _job_confidence(
    *,
    role_category: str,
    required_skills: list[str],
    responsibilities: list[str],
    evidence: list[dict[str, object]],
    warnings: list[str],
) -> float:
    score = 0.45
    if role_category in ROLE_CATEGORIES and role_category != "Other":
        score += 0.15
    if required_skills:
        score += min(0.18, len(required_skills) * 0.04)
    if responsibilities:
        score += 0.12
    if evidence:
        score += 0.08
    score -= min(0.25, len(warnings) * 0.06)
    return round(max(0.05, min(0.95, score)), 2)


def _risk_level(confidence: float, warnings: list[str]) -> str:
    if confidence < 0.45 or "invalid_or_sparse_jd_text" in warnings:
        return "high"
    if confidence < 0.65 or warnings:
        return "medium"
    return "low"


def _summary(
    role_category: str,
    required_skills: list[str],
    preferred_skills: list[str],
    warnings: list[str],
) -> str:
    parts = [f"{role_category} parser foundation profile"]
    if required_skills:
        parts.append("required: " + ", ".join(required_skills[:6]))
    if preferred_skills:
        parts.append("preferred: " + ", ".join(preferred_skills[:6]))
    if warnings:
        parts.append("review warnings present")
    return ". ".join(parts) + "."


def _looks_duplicate(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) >= 4 and len(set(lines)) <= len(lines) // 2:
        return True
    words = re.findall(r"[A-Za-z\u4e00-\u9fff]{2,}", text.lower())
    return len(words) >= 30 and len(set(words)) / len(words) < 0.35


def _evidence_item(
    field: str, value: str, evidence_text: str, confidence: float
) -> dict[str, object]:
    return {
        "field": field,
        "value": value,
        "evidence_text": evidence_text[:500],
        "confidence": confidence,
    }


def _has_any(text: str, cues: tuple[str, ...]) -> bool:
    return any(cue in text for cue in cues)


def _has_role_term(text: str, cues: tuple[str, ...]) -> bool:
    for cue in cues:
        if re.search(rf"(?<![a-z0-9]){re.escape(cue)}(?![a-z0-9])", text):
            return True
    return False


def _has_backend_mobile_conflict(job_title: str, raw_text: str) -> bool:
    title = job_title.lower()
    combined = f"{job_title} {raw_text}".lower()
    backend_title = _has_role_term(title, ("backend", "api developer"))
    mobile_signal = _has_role_term(
        combined,
        ("mobile", "react native", "ios", "android", "offline sync"),
    )
    return backend_title and mobile_signal


def _dedupe(values: Any) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for value in values:
        key = str(value).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result
