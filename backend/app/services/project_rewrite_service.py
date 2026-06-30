import re
from typing import Iterable

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.tenant import require_owned
from app.models.job import JobDescription, JobProfile
from app.models.match import MatchReport
from app.models.profile import Profile
from app.models.project import Project
from app.models.resume import Resume, ResumeVersion
from app.repositories import project_repository
from app.schemas.projects import (
    ProjectEvidenceRequired,
    ProjectMatchedPoint,
    ProjectMissingPoint,
    ProjectRewriteRecord,
    ProjectRewriteRequest,
    ProjectRewrittenBullet,
    ProjectRiskFlag,
)


REWRITE_STRATEGY = "deterministic_project_rewrite_v1"

FORBIDDEN_CHANGES = [
    "company",
    "user_count",
    "revenue",
    "accuracy",
    "production_status",
    "business_scale",
    "tech_stack_not_in_facts",
    "unsupported_metric",
]

METRIC_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?\s*%|\d+(?:\.\d+)?\s*(ms|s|sec|seconds|users|requests|qps|rps|x|times|million|k)\b)",
    re.IGNORECASE,
)
NUMERIC_CLAIM_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\b")
CLAIM_TERMS = {
    "latency",
    "reduced",
    "improved",
    "increase",
    "decrease",
    "optimized",
    "accuracy",
    "commercial",
    "revenue",
    "users",
    "traffic",
    "production",
    "launch",
    "上线",
    "收益",
    "准确率",
}
LEARNING_CONTEXT_TERMS = {
    "learning",
    "local",
    "synthetic",
    "experiment",
    "course",
    "demo",
    "prototype",
    "学习",
    "本地",
    "实验",
}
BUSINESS_OUTCOME_TERMS = {
    "production",
    "launch",
    "commercial",
    "revenue",
    "users",
    "million",
    "上线",
    "商业",
    "收益",
    "用户",
}
PRIVATE_TEXT_KEYS = {
    "raw_text",
    "raw_text_preview",
    "resume_text",
    "full_text",
    "source_text",
}


def create_project_rewrite(
    db: Session,
    project_id: str,
    payload: ProjectRewriteRequest,
) -> ProjectRewriteRecord:
    project = _get_project(db, project_id)
    _, job_profile = _latest_job_profile(db, payload.jd_id)
    resume_version_id = _validate_resume_version(db, payload.resume_version_id)
    match_report_id = _validate_match_report(db, payload.match_report_id)
    profile_id = _validate_profile(db, payload.profile_id)
    _validate_project_facts(project)

    fact_candidates = _collect_fact_candidates(project)
    matched_points, missing_points = _match_project_to_jd(
        fact_candidates,
        required_skills=list(job_profile.required_skills or []),
        preferred_skills=list(job_profile.preferred_skills or []),
    )
    evidence_required = _build_evidence_required(project)
    risk_flags = _build_risk_flags(
        missing_points=missing_points,
        evidence_required=evidence_required,
    )
    rewritten_bullets = _build_rewritten_bullets(
        project,
        matched_points=matched_points,
        evidence_required=evidence_required,
    )

    return project_repository.create_project_rewrite(
        db,
        project_id=project.id,
        jd_id=payload.jd_id.strip(),
        resume_version_id=resume_version_id,
        match_report_id=match_report_id,
        profile_id=profile_id,
        matched_points=[point.model_dump() for point in matched_points],
        missing_points=[point.model_dump() for point in missing_points],
        evidence_required=[item.model_dump() for item in evidence_required],
        rewritten_bullets=[bullet.model_dump() for bullet in rewritten_bullets],
        forbidden_changes=FORBIDDEN_CHANGES,
        risk_flags=[flag.model_dump() for flag in risk_flags],
        rewrite_strategy=REWRITE_STRATEGY,
    )


def get_project_rewrite(db: Session, rewrite_id: str) -> ProjectRewriteRecord:
    return project_repository.get_project_rewrite(db, rewrite_id)


def _get_project(db: Session, project_id: str) -> Project:
    project = project_repository.get_project_model(db, project_id)
    if not project:
        raise AppError(
            code="project_not_found",
            message="Project was not found.",
            status_code=404,
            details={"project_id": project_id},
        )
    return project


def _latest_job_profile(db: Session, jd_id: str) -> tuple[JobDescription, JobProfile]:
    job = db.get(JobDescription, jd_id.strip())
    require_owned(
        job,
        code="job_not_found",
        message="JD was not found.",
        details={"jd_id": jd_id},
    )
    if not job or job.status != "active":
        raise AppError(
            code="job_not_found",
            message="JD was not found.",
            status_code=404,
            details={"jd_id": jd_id},
        )
    profile = (
        db.query(JobProfile)
        .filter(JobProfile.jd_id == job.id)
        .order_by(JobProfile.profile_version.desc(), JobProfile.created_at.desc())
        .first()
    )
    if not profile:
        raise AppError(
            code="job_not_found",
            message="JD profile was not found.",
            status_code=404,
            details={"jd_id": jd_id},
        )
    return job, profile


def _validate_resume_version(db: Session, resume_version_id: str | None) -> str | None:
    normalized = _normalize_optional_id(resume_version_id, "resume_version_id")
    if normalized is None:
        return None
    version = db.get(ResumeVersion, normalized)
    resume = db.get(Resume, version.resume_id) if version else None
    require_owned(
        resume,
        code="resume_version_not_found",
        message="Resume version was not found.",
        details={"resume_version_id": normalized},
    )
    if version is None:
        raise AppError(
            code="resume_version_not_found",
            message="Resume version was not found.",
            status_code=404,
            details={"resume_version_id": normalized},
        )
    return normalized


def _validate_match_report(db: Session, match_report_id: str | None) -> str | None:
    normalized = _normalize_optional_id(match_report_id, "match_report_id")
    if normalized is None:
        return None
    match_report = db.get(MatchReport, normalized)
    require_owned(
        match_report,
        code="match_report_not_found",
        message="Match report was not found.",
        details={"match_report_id": normalized},
    )
    if match_report is None:
        raise AppError(
            code="match_report_not_found",
            message="Match report was not found.",
            status_code=404,
            details={"match_report_id": normalized},
        )
    return normalized


def _validate_profile(db: Session, profile_id: str | None) -> str | None:
    normalized = _normalize_optional_id(profile_id, "profile_id")
    if normalized is None:
        return None
    profile = db.get(Profile, normalized)
    require_owned(
        profile,
        code="profile_not_found",
        message="Profile was not found.",
        details={"profile_id": normalized},
    )
    if profile is None:
        raise AppError(
            code="profile_not_found",
            message="Profile was not found.",
            status_code=404,
            details={"profile_id": normalized},
        )
    return normalized


def _normalize_optional_id(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise AppError(
            code="validation_error",
            message=f"{field_name} must not be empty.",
            status_code=400,
            details={"field": field_name},
        )
    return normalized


def _validate_project_facts(project: Project) -> None:
    has_facts = any(
        [
            _clean_text(project.background),
            _clean_list(project.tech_stack),
            _clean_list(project.responsibilities),
            _clean_list(project.results),
            list(project.evidence or []),
        ]
    )
    if not has_facts:
        raise AppError(
            code="project_facts_insufficient",
            message="Project facts are required before running deterministic rewrite.",
            status_code=400,
            details={"project_id": project.id},
        )


def _collect_fact_candidates(project: Project) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    for skill in _clean_list(project.tech_stack):
        candidates.append(("tech_stack", skill))
    for item in _clean_list(project.responsibilities):
        candidates.append(("responsibilities", item))
    for item in _clean_list(project.results):
        candidates.append(("results", item))
    for item in project.evidence or []:
        candidates.append(("evidence", _evidence_to_search_text(item)))
    background = _clean_text(project.background)
    if background:
        candidates.append(("background", background))
    return [(field, text) for field, text in candidates if text]


def _match_project_to_jd(
    fact_candidates: list[tuple[str, str]],
    *,
    required_skills: list[str],
    preferred_skills: list[str],
) -> tuple[list[ProjectMatchedPoint], list[ProjectMissingPoint]]:
    matched_points: list[ProjectMatchedPoint] = []
    missing_points: list[ProjectMissingPoint] = []
    seen_matches: set[tuple[str, str]] = set()

    for skill in _dedupe_clean(required_skills):
        match = _find_skill_match(skill, fact_candidates)
        if match:
            source_field, project_text = match
            key = (skill.casefold(), "required_skill")
            if key not in seen_matches:
                matched_points.append(
                    ProjectMatchedPoint(
                        skill=skill,
                        source_field=source_field,
                        project_text=project_text,
                        jd_requirement=skill,
                        match_type="required_skill",
                    )
                )
                seen_matches.add(key)
        else:
            missing_points.append(
                ProjectMissingPoint(
                    requirement=skill,
                    requirement_type="required_skill",
                    reason="Project facts do not mention this required JD skill.",
                    priority="high",
                )
            )

    for skill in _dedupe_clean(preferred_skills):
        match = _find_skill_match(skill, fact_candidates)
        if match:
            source_field, project_text = match
            key = (skill.casefold(), "preferred_skill")
            if key not in seen_matches:
                matched_points.append(
                    ProjectMatchedPoint(
                        skill=skill,
                        source_field=source_field,
                        project_text=project_text,
                        jd_requirement=skill,
                        match_type="preferred_skill",
                    )
                )
                seen_matches.add(key)
        else:
            missing_points.append(
                ProjectMissingPoint(
                    requirement=skill,
                    requirement_type="preferred_skill",
                    reason="Project facts do not mention this preferred JD skill.",
                    priority="medium",
                )
            )

    return matched_points, missing_points


def _build_evidence_required(project: Project) -> list[ProjectEvidenceRequired]:
    evidence_text = _project_evidence_text(project)
    learning_context = _has_learning_context(project)
    required: list[ProjectEvidenceRequired] = []
    for source_field, text in _claim_sources(project):
        if not text or _has_supporting_evidence(evidence_text, text):
            continue
        if learning_context and _has_business_outcome_claim(text):
            required.append(
                ProjectEvidenceRequired(
                    type="timeline_or_scope_evidence",
                    source_field=source_field,
                    project_text=text,
                    reason=(
                        "Learning or local project claims production/business scope "
                        "and requires explicit supporting evidence."
                    ),
                )
            )
        elif _has_metric_claim(text):
            required.append(
                ProjectEvidenceRequired(
                    type="unsupported_metric",
                    source_field=source_field,
                    project_text=text,
                    reason="Metric or quantified impact requires supporting evidence.",
                )
            )
        elif _has_scope_or_outcome_claim(text):
            required.append(
                ProjectEvidenceRequired(
                    type="missing_evidence",
                    source_field=source_field,
                    project_text=text,
                    reason="Outcome or scope claim requires supporting evidence.",
                )
            )
    return required


def _project_evidence_text(project: Project) -> str:
    return " ".join(
        _evidence_to_search_text(item) for item in list(project.evidence or [])
    ).casefold()


def _has_supporting_evidence(evidence_text: str, claim_text: str) -> bool:
    if not evidence_text:
        return False
    markers = _claim_markers(claim_text)
    if markers:
        return any(marker.casefold() in evidence_text for marker in markers)
    return any(
        term in claim_text.casefold() and term in evidence_text
        for term in CLAIM_TERMS
    )


def _claim_markers(text: str) -> list[str]:
    markers = [match.group(0).strip() for match in METRIC_PATTERN.finditer(text)]
    if markers:
        return markers
    return [match.group(0).strip() for match in NUMERIC_CLAIM_PATTERN.finditer(text)]


def _build_risk_flags(
    *,
    missing_points: list[ProjectMissingPoint],
    evidence_required: list[ProjectEvidenceRequired],
) -> list[ProjectRiskFlag]:
    risk_flags: list[ProjectRiskFlag] = []
    seen: set[tuple[str, str]] = set()

    for point in missing_points:
        severity = "high" if point.requirement_type == "required_skill" else "medium"
        key = ("fabricated_skill", point.requirement.casefold())
        if key not in seen:
            risk_flags.append(
                ProjectRiskFlag(
                    type="fabricated_skill",
                    severity=severity,
                    source_field="jd_requirement",
                    message=(
                        f"Do not add {point.requirement} unless project facts and "
                        "evidence are updated by the user."
                    ),
                )
            )
            seen.add(key)

    for item in evidence_required:
        key = (item.type, item.project_text)
        if key in seen:
            continue
        if item.type == "unsupported_metric":
            risk_flags.append(
                ProjectRiskFlag(
                    type="unsupported_metric",
                    severity="high",
                    source_field=item.source_field,
                    message="Quantified result must be supported before reuse.",
                )
            )
            risk_flags.append(
                ProjectRiskFlag(
                    type="missing_evidence",
                    severity="medium",
                    source_field=item.source_field,
                    message="Evidence is missing for a metric or impact claim.",
                )
            )
            risk_flags.append(
                ProjectRiskFlag(
                    type="overclaim",
                    severity="medium",
                    source_field=item.source_field,
                    message="Do not strengthen this quantified claim without proof.",
                )
            )
        else:
            risk_flags.append(
                ProjectRiskFlag(
                    type="missing_evidence",
                    severity="medium",
                    source_field=item.source_field,
                    message="Evidence is missing for this project claim.",
                )
            )
            if item.type == "timeline_or_scope_evidence":
                risk_flags.append(
                    ProjectRiskFlag(
                        type="overclaim",
                        severity="high",
                        source_field=item.source_field,
                        message="Do not convert learning project scope into business outcome without proof.",
                    )
                )
                risk_flags.append(
                    ProjectRiskFlag(
                        type="learning_to_business_overclaim",
                        severity="high",
                        source_field=item.source_field,
                        message=(
                            "Learning/local project context conflicts with claimed "
                            "production or business impact."
                        ),
                    )
                )
        seen.add(key)

    return risk_flags


def _build_rewritten_bullets(
    project: Project,
    *,
    matched_points: list[ProjectMatchedPoint],
    evidence_required: list[ProjectEvidenceRequired],
) -> list[ProjectRewrittenBullet]:
    bullets: list[ProjectRewrittenBullet] = []
    source_bullets = _clean_list(project.responsibilities) + _clean_list(project.results)
    if not source_bullets:
        background = _clean_text(project.background)
        if background:
            source_bullets = [background]

    for before in source_bullets:
        evidence_note = _evidence_note_for_text(before, evidence_required)
        after = _rewrite_without_fabrication(before, matched_points)
        bullets.append(
            ProjectRewrittenBullet(
                before=before,
                after=after,
                reason="Rewritten only from existing project facts and matched JD skills.",
                evidence_required=evidence_note,
                risk_level=_risk_level_for_bullet(evidence_note, before),
            )
        )
    return bullets


def _rewrite_without_fabrication(
    before: str,
    matched_points: list[ProjectMatchedPoint],
) -> str:
    matched_skill = _first_fact_backed_skill(before, matched_points)
    if not matched_skill:
        return before
    if _contains_skill(before, matched_skill):
        return before
    return f"{before} Relevant JD alignment: {matched_skill}."


def _first_fact_backed_skill(
    text: str,
    matched_points: list[ProjectMatchedPoint],
) -> str | None:
    for point in matched_points:
        if _contains_skill(text, point.skill):
            return point.skill
    for point in matched_points:
        if point.source_field == "tech_stack":
            return point.skill
    return None


def _risk_level_for_bullet(evidence_note: str, before: str) -> str:
    if not evidence_note:
        return "low"
    if _has_metric_claim(before):
        return "high"
    return "medium"


def _evidence_note_for_text(
    text: str,
    evidence_required: list[ProjectEvidenceRequired],
) -> str:
    for item in evidence_required:
        if item.project_text == text:
            return f"Evidence required: {item.reason}"
    return ""


def _claim_sources(project: Project) -> Iterable[tuple[str, str]]:
    for item in _clean_list(project.responsibilities):
        yield "responsibilities", item
    for item in _clean_list(project.results):
        yield "results", item
    background = _clean_text(project.background)
    if background:
        yield "background", background


def _has_metric_claim(text: str) -> bool:
    lowered = text.casefold()
    return bool(METRIC_PATTERN.search(text)) or (
        bool(NUMERIC_CLAIM_PATTERN.search(text))
        and any(term in lowered for term in CLAIM_TERMS)
    )


def _has_scope_or_outcome_claim(text: str) -> bool:
    lowered = text.casefold()
    return any(term in lowered for term in CLAIM_TERMS)


def _has_learning_context(project: Project) -> bool:
    context = " ".join(
        [
            str(project.name or ""),
            str(project.role or ""),
            str(project.background or ""),
        ]
    ).casefold()
    return any(term in context for term in LEARNING_CONTEXT_TERMS)


def _has_business_outcome_claim(text: str) -> bool:
    lowered = text.casefold()
    return any(term in lowered for term in BUSINESS_OUTCOME_TERMS)


def _find_skill_match(
    skill: str,
    fact_candidates: list[tuple[str, str]],
) -> tuple[str, str] | None:
    for source_field, project_text in fact_candidates:
        if _contains_skill(project_text, skill):
            return source_field, project_text
    return None


def _contains_skill(text: str, skill: str) -> bool:
    if not text or not skill:
        return False
    return re.search(rf"(?<![A-Za-z0-9]){re.escape(skill)}(?![A-Za-z0-9])", text, re.IGNORECASE) is not None


def _evidence_to_search_text(item: object) -> str:
    if isinstance(item, dict):
        parts: list[str] = []
        for key, value in item.items():
            if key in PRIVATE_TEXT_KEYS:
                continue
            parts.append(_evidence_to_search_text(value))
        return " ".join(part for part in parts if part)
    if isinstance(item, list):
        return " ".join(_evidence_to_search_text(value) for value in item)
    if item is None:
        return ""
    return str(item)


def _clean_text(value: str | None) -> str:
    return value.strip() if value else ""


def _clean_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned: list[str] = []
    for value in values:
        text = str(value).strip()
        if text:
            cleaned.append(text)
    return cleaned


def _dedupe_clean(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = value.strip()
        key = text.casefold()
        if text and key not in seen:
            cleaned.append(text)
            seen.add(key)
    return cleaned
