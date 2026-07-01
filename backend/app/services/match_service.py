import re
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.tenant import require_owned
from app.models.job import JobDescription, JobProfile
from app.models.resume import Resume, ResumeVersion
from app.repositories import match_repository
from app.schemas.matches import (
    MatchCompareItem,
    MatchCompareRequest,
    MatchCompareResponse,
    MatchEvidence,
    MatchReport,
    MatchRunRequest,
)


SCORING_METHOD = "deterministic_trustworthy_match_v1"
DIMENSION_WEIGHTS = {
    "skill_match": 0.25,
    "project_relevance": 0.30,
    "business_understanding": 0.15,
    "expression_quality": 0.10,
    "education_fit": 0.10,
    "risk_control": 0.10,
}
RISK_SEVERITY_PENALTY = {"low": 1, "medium": 3, "high": 5}
METRIC_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?\s*%|\d+(?:\.\d+)?\s*(ms|s|sec|seconds|users|requests|qps|rps|x|times|million|k)\b)",
    re.IGNORECASE,
)
OVERCLAIM_TERMS = {
    "production",
    "launched",
    "commercial",
    "revenue",
    "million",
    "accuracy",
    "上线",
    "商业",
    "收益",
    "准确率",
}
BUSINESS_TERMS = (
    "workflow",
    "users",
    "user",
    "platform",
    "operations",
    "analytics",
    "stakeholder",
    "business",
    "customer",
    "enterprise",
    "candidate",
    "业务",
    "用户",
    "客户",
)
DEGREE_TERMS = {
    "bachelor",
    "master",
    "phd",
    "doctor",
    "本科",
    "学士",
    "硕士",
    "博士",
}


def flatten_resume_skills(structured_resume: dict[str, object]) -> set[str]:
    flattened: set[str] = set()
    skills = structured_resume.get("skills")
    if not isinstance(skills, dict):
        return flattened
    for values in skills.values():
        if isinstance(values, list):
            flattened.update(str(value).strip() for value in values if str(value).strip())
    return flattened


def _get_resume(db: Session, resume_id: str) -> Resume:
    resume = db.get(Resume, resume_id)
    require_owned(
        resume,
        code="resume_not_found",
        message="Resume was not found.",
        details={"resume_id": resume_id},
    )
    if not resume or resume.status != "active":
        raise AppError(
            code="resume_not_found",
            message="Resume was not found.",
            status_code=404,
            details={"resume_id": resume_id},
        )
    return resume


def _get_resume_version(db: Session, resume_version_id: str) -> ResumeVersion:
    version = db.get(ResumeVersion, resume_version_id)
    resume = db.get(Resume, version.resume_id) if version else None
    require_owned(
        resume,
        code="resume_version_not_found",
        message="Resume version was not found.",
        details={"resume_version_id": resume_version_id},
    )
    if not version:
        raise AppError(
            code="resume_version_not_found",
            message="Resume version was not found.",
            status_code=404,
            details={"resume_version_id": resume_version_id},
        )
    return version


def _latest_active_resume_version(db: Session, resume_id: str) -> ResumeVersion:
    _get_resume(db, resume_id)
    version = (
        db.query(ResumeVersion)
        .filter(ResumeVersion.resume_id == resume_id)
        .filter(ResumeVersion.status == "active")
        .order_by(ResumeVersion.version_number.desc(), ResumeVersion.created_at.desc())
        .first()
    )
    if not version:
        raise AppError(
            code="resume_version_not_found",
            message="Active resume version was not found.",
            status_code=404,
            details={"resume_id": resume_id},
        )
    return version


def _resolve_resume_version(db: Session, payload: MatchRunRequest) -> ResumeVersion:
    if payload.resume_version_id:
        version = _get_resume_version(db, payload.resume_version_id)
        if payload.resume_id:
            _get_resume(db, payload.resume_id)
            if version.resume_id != payload.resume_id:
                raise AppError(
                    code="resume_version_mismatch",
                    message="Resume version does not belong to the given resume.",
                    status_code=400,
                    details={
                        "resume_id": payload.resume_id,
                        "resume_version_id": payload.resume_version_id,
                    },
                )
        return version

    if not payload.resume_id:
        raise AppError(
            code="validation_error",
            message="Either resume_id or resume_version_id is required.",
            status_code=422,
            details={"fields": ["resume_id", "resume_version_id"]},
        )
    return _latest_active_resume_version(db, payload.resume_id)


def _latest_job_profile(db: Session, jd_id: str) -> tuple[JobDescription, JobProfile]:
    job = db.get(JobDescription, jd_id)
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
        .filter(JobProfile.jd_id == jd_id)
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


def run_match_report(db: Session, payload: MatchRunRequest) -> MatchReport:
    resume_version = _resolve_resume_version(db, payload)
    _, job_profile = _latest_job_profile(db, payload.jd_id)
    structured_resume = dict(resume_version.structured_resume or {})
    scoring = _score_match(structured_resume, resume_version, job_profile)

    return match_repository.create_match_report(
        db,
        resume_version_id=resume_version.id,
        jd_id=payload.jd_id,
        job_profile_id=job_profile.id,
        total_score=scoring["total_score"],
        dimension_scores=scoring["dimension_scores"],
        evidence=scoring["evidence"],
        strengths=scoring["strengths"],
        gaps=scoring["gaps"],
        rewrite_priorities=scoring["rewrite_priorities"],
        risk_flags=scoring["risk_flags"],
        recommended_projects=scoring["recommended_projects"],
        score_breakdown=scoring["score_breakdown"],
        scoring_method=SCORING_METHOD,
        confidence=scoring["confidence"],
    )


def compare_matches(db: Session, payload: MatchCompareRequest) -> MatchCompareResponse:
    mode = _compare_mode(payload)
    reports: list[MatchReport] = []
    if mode == "same_jd_multiple_resumes":
        assert payload.jd_id is not None
        for resume_version_id in payload.resume_version_ids:
            reports.append(
                run_match_report(
                    db,
                    MatchRunRequest(
                        resume_version_id=resume_version_id,
                        jd_id=payload.jd_id,
                    ),
                )
            )
    else:
        assert payload.resume_version_id is not None
        for jd_id in payload.jd_ids:
            reports.append(
                run_match_report(
                    db,
                    MatchRunRequest(
                        resume_version_id=payload.resume_version_id,
                        jd_id=jd_id,
                    ),
                )
            )

    sorted_reports = sorted(reports, key=lambda report: report.total_score, reverse=True)
    top_score = sorted_reports[0].total_score if sorted_reports else 0
    return MatchCompareResponse(
        compare_mode=mode,
        items=[
            MatchCompareItem(
                rank=index + 1,
                match_report_id=report.match_report_id,
                resume_id=report.resume_id,
                resume_version_id=report.resume_version_id,
                jd_id=report.jd_id,
                total_score=report.total_score,
                score_delta_from_top=top_score - report.total_score,
                main_strengths=report.strengths[:3],
                main_gaps=report.gaps[:3],
                risk_flags=report.risk_flags,
                dimension_scores=report.dimension_scores,
            )
            for index, report in enumerate(sorted_reports)
        ],
    )


def list_match_reports(
    db: Session,
    *,
    jd_id: str | None = None,
    resume_version_id: str | None = None,
) -> list[MatchReport]:
    return match_repository.list_match_reports(
        db,
        jd_id=jd_id,
        resume_version_id=resume_version_id,
    )


def get_match_report(db: Session, match_report_id: str) -> MatchReport:
    return match_repository.get_match_report(db, match_report_id)


def _compare_mode(payload: MatchCompareRequest) -> str:
    has_resume_set = bool(payload.jd_id and payload.resume_version_ids)
    has_jd_set = bool(payload.resume_version_id and payload.jd_ids)
    if has_resume_set == has_jd_set:
        raise AppError(
            code="validation_error",
            message=(
                "Provide either jd_id with resume_version_ids or resume_version_id "
                "with jd_ids."
            ),
            status_code=422,
            details={"fields": ["jd_id", "resume_version_ids", "resume_version_id", "jd_ids"]},
        )
    if has_resume_set:
        if len(payload.resume_version_ids) < 2:
            raise AppError(
                code="validation_error",
                message="At least two resume versions are required for comparison.",
                status_code=422,
                details={"field": "resume_version_ids"},
            )
        return "same_jd_multiple_resumes"
    if len(payload.jd_ids) < 2:
        raise AppError(
            code="validation_error",
            message="At least two JDs are required for comparison.",
            status_code=422,
            details={"field": "jd_ids"},
        )
    return "same_resume_multiple_jds"


def _score_match(
    structured_resume: dict[str, object],
    resume_version: ResumeVersion,
    job_profile: JobProfile,
) -> dict[str, Any]:
    required_skills = _dedupe_clean(job_profile.required_skills or [])
    preferred_skills = _dedupe_clean(job_profile.preferred_skills or [])
    resume_skills = flatten_resume_skills(structured_resume)
    resume_text = _flatten_text(structured_resume)
    projects = _record_list(structured_resume.get("projects"))
    project_text = _flatten_text(projects)
    education = _record_list(structured_resume.get("education"))
    education_text = _flatten_text(education)
    evidence_text = _flatten_text(structured_resume.get("evidence", []))

    matched_required = _matched_terms(required_skills, resume_text, resume_skills)
    missing_required = [skill for skill in required_skills if skill not in matched_required]
    matched_preferred = _matched_terms(preferred_skills, resume_text, resume_skills)
    missing_preferred = [skill for skill in preferred_skills if skill not in matched_preferred]
    project_required = _matched_terms(required_skills, project_text, set())
    project_preferred = _matched_terms(preferred_skills, project_text, set())
    project_missing_required = [
        skill for skill in required_skills if skill not in project_required
    ]
    business_terms = _business_requirements(job_profile)
    business_hits = _matched_terms(business_terms, resume_text, set())

    risk_flags = _build_match_risk_flags(
        structured_resume=structured_resume,
        resume_version=resume_version,
        required_skills=required_skills,
        matched_required=matched_required,
        project_required=project_required,
        resume_text=resume_text,
        project_text=project_text,
        evidence_text=evidence_text,
    )
    risk_penalty = _risk_penalty(risk_flags)

    required_rate = _rate(len(matched_required), len(required_skills))
    preferred_rate = _rate(len(matched_preferred), len(preferred_skills))
    project_required_rate = _rate(len(project_required), len(required_skills))
    project_preferred_rate = _rate(len(project_preferred), len(preferred_skills))
    business_rate = _rate(len(business_hits), len(business_terms))

    dimension_scores = {
        "skill_match": _clamp_int(
            35 + round(48 * required_rate) + round(12 * preferred_rate)
        ),
        "project_relevance": _clamp_int(
            35 + round(48 * project_required_rate) + round(12 * project_preferred_rate)
        )
        if projects
        else 30,
        "business_understanding": _business_score(business_terms, business_rate, resume_text),
        "expression_quality": _expression_score(structured_resume, projects),
        "education_fit": _education_score(education_text, job_profile),
        "risk_control": _clamp_int(95 - min(55, risk_penalty * 4)),
    }
    weighted_score = round(
        sum(
            dimension_scores[dimension] * weight
            for dimension, weight in DIMENSION_WEIGHTS.items()
        ),
        2,
    )
    total_risk_deduction = min(14, risk_penalty)
    total_score = _clamp_int(round(weighted_score - total_risk_deduction))
    evidence = _build_dimension_evidence(
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        matched_required=matched_required,
        missing_required=missing_required,
        project_required=project_required,
        project_missing_required=project_missing_required,
        business_terms=business_terms,
        business_hits=business_hits,
        education_text=education_text,
        risk_flags=risk_flags,
        dimension_scores=dimension_scores,
    )
    strengths = _build_strengths(
        matched_required,
        matched_preferred,
        project_required,
        business_hits,
    )
    gaps = _build_gaps(
        missing_required,
        missing_preferred,
        project_missing_required,
        business_terms,
        business_hits,
        risk_flags,
    )
    rewrite_priorities = _build_rewrite_priorities(
        missing_required,
        project_missing_required,
        business_terms,
        business_hits,
        risk_flags,
    )
    recommended_projects = _recommended_projects(projects, required_skills, preferred_skills)
    confidence = _match_confidence(
        structured_resume=structured_resume,
        required_skills=required_skills,
        evidence=evidence,
        risk_flags=risk_flags,
    )
    score_breakdown = {
        "weights": DIMENSION_WEIGHTS,
        "weighted_score": weighted_score,
        "risk_penalty": total_risk_deduction,
        "final_score": total_score,
        "matched_required_skills": matched_required,
        "missing_required_skills": missing_required,
        "matched_preferred_skills": matched_preferred,
        "missing_preferred_skills": missing_preferred,
        "project_supported_required_skills": project_required,
        "project_missing_required_skills": project_missing_required,
        "risk_deductions": [
            {
                "type": flag.get("type"),
                "severity": flag.get("severity"),
                "penalty": RISK_SEVERITY_PENALTY.get(str(flag.get("severity")), 0),
            }
            for flag in risk_flags
        ],
        "foundation_only": True,
    }
    return {
        "total_score": total_score,
        "dimension_scores": dimension_scores,
        "evidence": evidence,
        "strengths": strengths,
        "gaps": gaps,
        "rewrite_priorities": rewrite_priorities,
        "risk_flags": risk_flags,
        "recommended_projects": recommended_projects,
        "score_breakdown": score_breakdown,
        "confidence": confidence,
    }


def _build_dimension_evidence(
    *,
    required_skills: list[str],
    preferred_skills: list[str],
    matched_required: list[str],
    missing_required: list[str],
    project_required: list[str],
    project_missing_required: list[str],
    business_terms: list[str],
    business_hits: list[str],
    education_text: str,
    risk_flags: list[dict[str, object]],
    dimension_scores: dict[str, int],
) -> list[MatchEvidence]:
    return [
        MatchEvidence(
            dimension="skill_match",
            jd_requirement=", ".join(required_skills + preferred_skills) or "unspecified",
            resume_signal=", ".join(matched_required + project_required) or None,
            score_impact="positive" if matched_required else "negative",
            source="structured_resume.skills/projects",
            confidence=_score_confidence(dimension_scores["skill_match"]),
        ),
        MatchEvidence(
            dimension="project_relevance",
            jd_requirement=", ".join(required_skills) or "project evidence required",
            resume_signal=", ".join(project_required) or None,
            score_impact="positive" if project_required else "negative",
            source="structured_resume.projects",
            confidence=_score_confidence(dimension_scores["project_relevance"]),
        ),
        MatchEvidence(
            dimension="business_understanding",
            jd_requirement=", ".join(business_terms) or "business context unspecified",
            resume_signal=", ".join(business_hits) or None,
            score_impact="positive" if business_hits else "neutral",
            source="job_profile.business_scenarios/resume.projects",
            confidence=_score_confidence(dimension_scores["business_understanding"]),
        ),
        MatchEvidence(
            dimension="expression_quality",
            jd_requirement="Clear responsibilities, results, and evidence.",
            resume_signal=(
                "Project evidence is structured."
                if not missing_required and not project_missing_required
                else "Project evidence needs tightening."
            ),
            score_impact="positive"
            if dimension_scores["expression_quality"] >= 70
            else "neutral",
            source="structured_resume.projects/evidence",
            confidence=_score_confidence(dimension_scores["expression_quality"]),
        ),
        MatchEvidence(
            dimension="education_fit",
            jd_requirement="Education or training supports the target role.",
            resume_signal=education_text[:180] or None,
            score_impact="positive" if education_text else "neutral",
            source="structured_resume.education",
            confidence=_score_confidence(dimension_scores["education_fit"]),
        ),
        MatchEvidence(
            dimension="risk_control",
            jd_requirement="Avoid unsupported claims, weak evidence, and JD/project mismatch.",
            resume_signal=", ".join(str(flag.get("type")) for flag in risk_flags) or None,
            score_impact="negative" if risk_flags else "positive",
            source="structured_resume.risk_flags/match_rules",
            confidence=_score_confidence(dimension_scores["risk_control"]),
        ),
    ]


def _build_match_risk_flags(
    *,
    structured_resume: dict[str, object],
    resume_version: ResumeVersion,
    required_skills: list[str],
    matched_required: list[str],
    project_required: list[str],
    resume_text: str,
    project_text: str,
    evidence_text: str,
) -> list[dict[str, object]]:
    flags: list[dict[str, object]] = []
    for flag in _resume_risk_flags(structured_resume, resume_version):
        _add_risk_flag(
            flags,
            type=str(flag.get("type") or "resume_risk"),
            severity=str(flag.get("severity") or "medium"),
            source_field=str(flag.get("location") or flag.get("source_field") or "resume"),
            message=str(flag.get("message") or "Resume parser reported a risk flag."),
            evidence=str(flag.get("evidence") or ""),
        )

    if METRIC_PATTERN.search(resume_text) and not _has_metric_evidence(resume_text, evidence_text):
        _add_risk_flag(
            flags,
            type="unsupported_metric",
            severity="high",
            source_field="structured_resume.projects",
            message="Quantified impact appears without matching evidence.",
            evidence="metric_claim_without_evidence",
        )

    if any(term in resume_text.casefold() for term in OVERCLAIM_TERMS) and not evidence_text:
        _add_risk_flag(
            flags,
            type="overclaim",
            severity="medium",
            source_field="structured_resume.projects",
            message="Strong production or business claim needs supporting evidence.",
            evidence="strong_claim_without_evidence",
        )

    weak_skills = [skill for skill in matched_required if skill not in project_required]
    if weak_skills:
        _add_risk_flag(
            flags,
            type="weak_evidence",
            severity="medium",
            source_field="structured_resume.skills",
            message=(
                "Required skill is present in skills but not backed by project evidence: "
                + ", ".join(weak_skills)
            ),
            evidence=", ".join(weak_skills),
        )

    if required_skills and not project_required:
        _add_risk_flag(
            flags,
            type="project_jd_mismatch",
            severity="high",
            source_field="structured_resume.projects",
            message="Projects do not substantively support the required JD skills.",
            evidence=", ".join(required_skills),
        )

    if required_skills and not matched_required:
        _add_risk_flag(
            flags,
            type="missing_evidence",
            severity="medium",
            source_field="structured_resume.skills",
            message="No resume evidence matched the required JD skills.",
            evidence=", ".join(required_skills),
        )

    if "timeline" in _flatten_text(flags).casefold() or "conflict" in _flatten_text(flags).casefold():
        _add_risk_flag(
            flags,
            type="timeline_conflict",
            severity="medium",
            source_field="structured_resume",
            message="Timeline risk needs manual confirmation before scoring can be trusted.",
            evidence="parser_timeline_conflict",
        )

    return flags


def _resume_risk_flags(
    structured_resume: dict[str, object],
    resume_version: ResumeVersion,
) -> list[dict[str, object]]:
    flags: list[dict[str, object]] = []
    for source in (
        structured_resume.get("risk_flags"),
        resume_version.risk_flags,
        (resume_version.risk_report or {}).get("flags"),
        (resume_version.risk_report or {}).get("risk_flags"),
    ):
        if isinstance(source, list):
            flags.extend(item for item in source if isinstance(item, dict))
    return flags


def _add_risk_flag(
    flags: list[dict[str, object]],
    *,
    type: str,
    severity: str,
    source_field: str,
    message: str,
    evidence: str,
) -> None:
    normalized = type.strip() or "unknown"
    key = (normalized, source_field, evidence)
    existing = {
        (str(flag.get("type")), str(flag.get("source_field")), str(flag.get("evidence")))
        for flag in flags
    }
    if key in existing:
        return
    flags.append(
        {
            "type": normalized,
            "severity": severity if severity in RISK_SEVERITY_PENALTY else "medium",
            "source_field": source_field,
            "message": message,
            "evidence": evidence,
        }
    )


def _business_requirements(job_profile: JobProfile) -> list[str]:
    raw_terms: list[str] = []
    raw_terms.extend(str(item) for item in list(job_profile.business_scenarios or []))
    raw_terms.extend(str(item) for item in list(job_profile.responsibilities or []))
    for item in list(job_profile.hidden_requirements or []):
        if isinstance(item, dict):
            raw_terms.append(str(item.get("requirement") or item.get("title") or ""))
        else:
            raw_terms.append(str(item))
    candidates: list[str] = []
    for text in raw_terms:
        lowered = text.casefold()
        candidates.extend(term for term in BUSINESS_TERMS if term in lowered)
        candidates.extend(skill for skill in _dedupe_clean(job_profile.required_skills or []) if _contains_term(text, skill))
    return _dedupe_clean(candidates[:8])


def _business_score(
    business_terms: list[str],
    business_rate: float,
    resume_text: str,
) -> int:
    if not business_terms:
        return 65 if any(term in resume_text.casefold() for term in BUSINESS_TERMS) else 58
    return _clamp_int(45 + round(42 * business_rate))


def _expression_score(structured_resume: dict[str, object], projects: list[dict[str, object]]) -> int:
    evidence_count = len(_record_list(structured_resume.get("evidence")))
    warnings_count = len(list(structured_resume.get("warnings") or []))
    project_signal_count = 0
    for project in projects:
        project_signal_count += len(_value_list(project.get("responsibilities")))
        project_signal_count += len(_value_list(project.get("results")))
    score = 48 + min(22, evidence_count * 3) + min(20, project_signal_count * 4)
    score -= min(18, warnings_count * 4)
    return _clamp_int(score)


def _education_score(education_text: str, job_profile: JobProfile) -> int:
    if not education_text:
        return 48
    lowered = education_text.casefold()
    score = 62
    if any(term in lowered for term in DEGREE_TERMS):
        score += 13
    role_words = [
        word
        for word in re.split(r"[^A-Za-z0-9]+", str(job_profile.role_category or ""))
        if len(word) >= 4
    ]
    if any(word.casefold() in lowered for word in role_words):
        score += 6
    if any(term in lowered for term in ("software", "computer", "data", "analytics", "it")):
        score += 7
    return _clamp_int(score)


def _build_strengths(
    matched_required: list[str],
    matched_preferred: list[str],
    project_required: list[str],
    business_hits: list[str],
) -> list[str]:
    strengths: list[str] = []
    if matched_required:
        strengths.append("Matched required skills: " + ", ".join(matched_required))
    if project_required:
        strengths.append("Project evidence supports: " + ", ".join(project_required))
    if matched_preferred:
        strengths.append("Matched preferred skills: " + ", ".join(matched_preferred))
    if business_hits:
        strengths.append("Business context signals: " + ", ".join(business_hits))
    return strengths or ["Resume has a parseable structure but needs stronger JD evidence."]


def _build_gaps(
    missing_required: list[str],
    missing_preferred: list[str],
    project_missing_required: list[str],
    business_terms: list[str],
    business_hits: list[str],
    risk_flags: list[dict[str, object]],
) -> list[str]:
    gaps: list[str] = []
    if missing_required:
        gaps.append("Missing required skills: " + ", ".join(missing_required))
    if project_missing_required:
        gaps.append(
            "Required skills lacking project evidence: "
            + ", ".join(project_missing_required)
        )
    if missing_preferred:
        gaps.append("Missing preferred skills: " + ", ".join(missing_preferred))
    missing_business = [term for term in business_terms if term not in business_hits]
    if missing_business:
        gaps.append("Business understanding needs evidence for: " + ", ".join(missing_business))
    if risk_flags:
        gaps.append(
            "Risk control issues: "
            + ", ".join(_dedupe_clean([str(flag.get("type")) for flag in risk_flags]))
        )
    return gaps or ["No material deterministic gap detected; manual review still required."]


def _build_rewrite_priorities(
    missing_required: list[str],
    project_missing_required: list[str],
    business_terms: list[str],
    business_hits: list[str],
    risk_flags: list[dict[str, object]],
) -> list[str]:
    priorities: list[str] = []
    for skill in project_missing_required[:3]:
        priorities.append(f"Add project-backed evidence for required skill: {skill}.")
    for skill in missing_required[:3]:
        priorities.append(f"Do not claim {skill} unless the user adds verified evidence.")
    missing_business = [term for term in business_terms if term not in business_hits]
    for term in missing_business[:2]:
        priorities.append(f"Clarify business scenario evidence for: {term}.")
    if risk_flags:
        priorities.append(
            "Resolve risk flags before rewrite: "
            + ", ".join(_dedupe_clean([str(flag.get("type")) for flag in risk_flags]))[:160]
        )
    return priorities or ["Prioritize concise evidence-backed project bullets."]


def _recommended_projects(
    projects: list[dict[str, object]],
    required_skills: list[str],
    preferred_skills: list[str],
) -> list[dict[str, object]]:
    ranked: list[dict[str, object]] = []
    for index, project in enumerate(projects):
        text = _flatten_text(project)
        matched_required = _matched_terms(required_skills, text, set())
        matched_preferred = _matched_terms(preferred_skills, text, set())
        score = len(matched_required) * 3 + len(matched_preferred)
        name = str(project.get("name") or project.get("title") or f"project_{index + 1}")
        ranked.append(
            {
                "rank": 0,
                "project_ref": name,
                "score": score,
                "matched_required_skills": matched_required,
                "matched_preferred_skills": matched_preferred,
            }
        )
    ranked.sort(key=lambda item: int(item["score"]), reverse=True)
    for index, item in enumerate(ranked):
        item["rank"] = index + 1
    return ranked


def _match_confidence(
    *,
    structured_resume: dict[str, object],
    required_skills: list[str],
    evidence: list[MatchEvidence],
    risk_flags: list[dict[str, object]],
) -> float:
    parse_confidence = structured_resume.get("parse_confidence")
    base = float(parse_confidence) if isinstance(parse_confidence, int | float) else 0.55
    evidence_rate = _rate(
        sum(1 for item in evidence if item.resume_signal),
        len(evidence),
    )
    required_bonus = 0.08 if required_skills else -0.05
    risk_penalty = min(0.25, len(risk_flags) * 0.04)
    return round(max(0.0, min(1.0, base * 0.55 + evidence_rate * 0.35 + required_bonus - risk_penalty)), 4)


def _risk_penalty(risk_flags: list[dict[str, object]]) -> int:
    return sum(
        RISK_SEVERITY_PENALTY.get(str(flag.get("severity")), 3)
        for flag in risk_flags
    )


def _has_metric_evidence(resume_text: str, evidence_text: str) -> bool:
    if not evidence_text:
        return False
    markers = [match.group(0).casefold() for match in METRIC_PATTERN.finditer(resume_text)]
    return bool(markers) and any(marker in evidence_text.casefold() for marker in markers)


def _matched_terms(
    terms: list[str],
    text: str,
    skill_set: set[str],
) -> list[str]:
    skill_lookup = {skill.casefold(): skill for skill in skill_set}
    matched: list[str] = []
    for term in terms:
        key = term.casefold()
        if key in skill_lookup or _contains_term(text, term):
            matched.append(term)
    return _dedupe_clean(matched)


def _contains_term(text: str, term: str) -> bool:
    if not text or not term:
        return False
    lowered = text.casefold()
    needle = term.casefold()
    if not any(character.isalnum() for character in needle):
        return needle in lowered
    return re.search(rf"(?<![A-Za-z0-9]){re.escape(needle)}(?![A-Za-z0-9])", lowered) is not None


def _flatten_text(value: object) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten_text(child) for child in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    if value is None:
        return ""
    return str(value)


def _record_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _value_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _dedupe_clean(values: list[object]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        key = text.casefold()
        if text and key not in seen:
            cleaned.append(text)
            seen.add(key)
    return cleaned


def _rate(count: int, total: int) -> float:
    if total <= 0:
        return 1.0
    return count / total


def _clamp_int(value: int) -> int:
    return max(0, min(100, int(value)))


def _score_confidence(score: int) -> float:
    return round(max(0.0, min(1.0, score / 100)), 4)
