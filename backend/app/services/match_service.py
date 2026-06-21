from app.schemas.matches import MatchEvidence, MatchReport, MatchRunRequest
from app.schemas.resumes import ResumeRecord
from app.services.job_service import get_mock_job
from app.services.mock_store import store
from app.services.resume_service import get_mock_resume


def flatten_resume_skills(resume: ResumeRecord) -> set[str]:
    flattened: set[str] = set()
    for values in resume.structured_resume.skills.values():
        flattened.update(values)
    return flattened


def build_mock_report(payload: MatchRunRequest) -> MatchReport:
    resume = get_mock_resume(payload.resume_id)
    job = get_mock_job(payload.jd_id)
    resume_skills = flatten_resume_skills(resume)
    required_skills = set(job.job_profile.required_skills)
    matched_skills = sorted(required_skills & resume_skills)
    missing_skills = sorted(required_skills - resume_skills)
    coverage = len(matched_skills) / len(required_skills) if required_skills else 0

    skill_score = 55 + round(40 * coverage)
    dimension_scores = {
        "skill_match": skill_score,
        "project_relevance": 65 if matched_skills else 55,
        "business_understanding": 60,
        "expression_quality": 62,
        "education_fit": 60,
        "risk_control": 80,
    }
    total_score = round(sum(dimension_scores.values()) / len(dimension_scores))
    match_report_id = store.next_id("match", len(store.matches))
    report = MatchReport(
        match_report_id=match_report_id,
        resume_id=payload.resume_id,
        jd_id=payload.jd_id,
        total_score=total_score,
        dimension_scores=dimension_scores,
        evidence=[
            MatchEvidence(
                dimension="skill_match",
                jd_requirement=", ".join(sorted(required_skills)) or "unspecified",
                resume_signal=", ".join(matched_skills) if matched_skills else None,
                score_impact="positive" if matched_skills else "neutral",
            )
        ],
        strengths=[
            "Matched required skills: " + ", ".join(matched_skills)
            if matched_skills
            else "Resume file passed Phase 1 validation."
        ],
        gaps=[
            "Missing required skills: " + ", ".join(missing_skills)
            if missing_skills
            else "No required skill gap detected by deterministic mock rules."
        ],
        rewrite_priorities=[
            "Confirm project facts and evidence before rewriting resume bullets."
        ],
        risk_flags=[],
    )
    store.matches[report.match_report_id] = report
    return report


def list_mock_matches() -> list[MatchReport]:
    return list(store.matches.values())


def get_mock_match(match_report_id: str) -> MatchReport:
    report = store.matches.get(match_report_id)
    if not report:
        from app.core.errors import AppError

        raise AppError(
            code="match_report_not_found",
            message="Match report was not found in the Phase 1 mock store.",
            status_code=404,
            details={"match_report_id": match_report_id},
        )
    return report
