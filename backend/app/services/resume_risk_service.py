from __future__ import annotations

import re
from collections import Counter
from typing import Any

from app.schemas.resumes import ResumeRiskFlag, StructuredResume


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


def evaluate_resume_risks(
    structured_resume: StructuredResume,
) -> tuple[list[ResumeRiskFlag], dict[str, object]]:
    flags: list[ResumeRiskFlag] = []
    declared_skills = _flatten_declared_skills(structured_resume.skills)

    for collection_name in ("education", "projects", "experience"):
        records = getattr(structured_resume, collection_name)
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                continue
            location = f"{collection_name}[{index}]"
            flags.extend(_timeline_flags(record, location))

    for index, project in enumerate(structured_resume.projects):
        if not isinstance(project, dict):
            continue
        location = f"projects[{index}]"
        flags.extend(_project_skill_flags(project, declared_skills, location))
        flags.extend(_project_evidence_flags(project, location))

    counter = Counter(flag.type for flag in flags)
    risk_report = {
        "passed": not flags,
        "summary": (
            "No deterministic resume risks detected."
            if not flags
            else f"{len(flags)} deterministic resume risk flag(s) detected."
        ),
        "flag_count": len(flags),
        "counts_by_type": dict(sorted(counter.items())),
        "rules": [
            "unsupported_metric",
            "fabricated_skill",
            "timeline_conflict",
            "missing_evidence",
            "overclaim",
        ],
        "flags": [flag.model_dump() for flag in flags],
    }
    return flags, risk_report


def _timeline_flags(record: dict[str, Any], location: str) -> list[ResumeRiskFlag]:
    start_key = _date_key(record.get("start_date"))
    end_key = _date_key(record.get("end_date"))
    if not start_key or not end_key:
        return []
    if start_key <= end_key:
        return []
    return [
        ResumeRiskFlag(
            type="timeline_conflict",
            severity="high",
            message="Start date is later than end date.",
            location=location,
            evidence=f"{record.get('start_date')} > {record.get('end_date')}",
        )
    ]


def _date_key(value: Any) -> tuple[int, int] | None:
    if not isinstance(value, str):
        return None
    lowered = value.strip().lower()
    if not lowered or lowered in {"present", "current", "now", "至今", "现在"}:
        return None
    match = re.search(r"(?P<year>(?:19|20)\d{2})(?:[-/.](?P<month>\d{1,2}))?", lowered)
    if not match:
        return None
    return int(match.group("year")), int(match.group("month") or 1)


def _project_skill_flags(
    project: dict[str, Any], declared_skills: set[str], location: str
) -> list[ResumeRiskFlag]:
    flags: list[ResumeRiskFlag] = []
    for skill in _as_list(project.get("tech_stack")):
        normalized = _normalize_skill(skill)
        if normalized and normalized not in declared_skills:
            flags.append(
                ResumeRiskFlag(
                    type="fabricated_skill",
                    severity="medium",
                    message="Project tech stack contains a skill that is not declared in skills.",
                    location=f"{location}.tech_stack",
                    evidence=str(skill),
                )
            )
    return flags


def _project_evidence_flags(project: dict[str, Any], location: str) -> list[ResumeRiskFlag]:
    flags: list[ResumeRiskFlag] = []
    evidence = _as_list(project.get("evidence"))
    has_evidence = any(str(item).strip() for item in evidence)
    claim_text = " ".join(
        str(item)
        for key in ("results", "responsibilities", "background")
        for item in _as_list(project.get(key))
    )
    if not claim_text.strip() or has_evidence:
        return flags

    if METRIC_RE.search(claim_text):
        flags.append(
            ResumeRiskFlag(
                type="unsupported_metric",
                severity="high",
                message="Metric or quantified outcome has no supporting evidence.",
                location=location,
                evidence=claim_text,
            )
        )

    if STRONG_CLAIM_RE.search(claim_text):
        flags.append(
            ResumeRiskFlag(
                type="overclaim",
                severity="medium",
                message="Strong production, scale, revenue, or expertise claim has no evidence.",
                location=location,
                evidence=claim_text,
            )
        )

    if _has_result_claim(project) and not flags:
        flags.append(
            ResumeRiskFlag(
                type="missing_evidence",
                severity="medium",
                message="Result claim has no supporting evidence.",
                location=location,
                evidence=claim_text,
            )
        )
    elif flags:
        flags.append(
            ResumeRiskFlag(
                type="missing_evidence",
                severity="medium",
                message="Claim requires user confirmation and supporting evidence.",
                location=location,
                evidence=claim_text,
            )
        )
    return flags


def _has_result_claim(project: dict[str, Any]) -> bool:
    return any(str(item).strip() for item in _as_list(project.get("results")))


def _flatten_declared_skills(skills: dict[str, list[str]]) -> set[str]:
    flattened: set[str] = set()
    for values in skills.values():
        for skill in values:
            normalized = _normalize_skill(skill)
            if normalized:
                flattened.add(normalized)
    return flattened


def _normalize_skill(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    return normalized or None


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
