from fastapi import APIRouter, Request, status

from app.core.errors import AppError
from app.schemas.common import ApiResponse, ListResponse
from app.schemas.matches import MatchEvidence, MatchReport, MatchRunRequest
from app.services.mock_store import store


router = APIRouter(prefix="/api/matches", tags=["matches"])


def build_mock_report(payload: MatchRunRequest) -> MatchReport:
    resume = store.resumes[payload.resume_id]
    job = store.jobs[payload.jd_id]
    required_skills = job.job_profile.required_skills
    skill_score = 70 if required_skills else 55
    dimension_scores = {
        "skill_match": skill_score,
        "project_relevance": 60,
        "business_understanding": 58,
        "expression_quality": 62,
        "education_fit": 60,
        "risk_control": 80,
    }
    total_score = round(sum(dimension_scores.values()) / len(dimension_scores))
    evidence = [
        MatchEvidence(
            dimension="skill_match",
            jd_requirement=", ".join(required_skills) if required_skills else "unspecified",
            resume_signal=resume.parse_status,
            score_impact="mock_positive" if required_skills else "mock_neutral",
        )
    ]
    match_report_id = store.next_id("match", len(store.matches))
    return MatchReport(
        match_report_id=match_report_id,
        resume_id=payload.resume_id,
        jd_id=payload.jd_id,
        total_score=total_score,
        dimension_scores=dimension_scores,
        evidence=evidence,
        strengths=["Mock strength: resume file passed Phase 1A validation."],
        gaps=[
            "Mock gap: structured project evidence is not available until later phases."
        ],
        rewrite_priorities=[
            "Mock priority: confirm project facts before any rewrite suggestion."
        ],
        risk_flags=[],
    )


@router.post(
    "/run",
    response_model=ApiResponse[MatchReport],
    status_code=status.HTTP_201_CREATED,
)
async def run_match(
    request: Request, payload: MatchRunRequest
) -> dict[str, object]:
    if payload.resume_id not in store.resumes:
        raise AppError(
            code="resume_not_found",
            message="Resume was not found in the Phase 1A mock store.",
            status_code=404,
            details={"resume_id": payload.resume_id},
        )
    if payload.jd_id not in store.jobs:
        raise AppError(
            code="job_not_found",
            message="JD was not found in the Phase 1A mock store.",
            status_code=404,
            details={"jd_id": payload.jd_id},
        )
    report = build_mock_report(payload)
    store.matches[report.match_report_id] = report
    return {"data": report, "request_id": request.state.request_id}


@router.get("", response_model=ApiResponse[ListResponse[MatchReport]])
async def list_matches(request: Request) -> dict[str, object]:
    items = list(store.matches.values())
    return {
        "data": ListResponse(items=items, total=len(items)),
        "request_id": request.state.request_id,
    }


@router.get("/{match_report_id}", response_model=ApiResponse[MatchReport])
async def get_match(
    request: Request, match_report_id: str
) -> dict[str, object]:
    report = store.matches.get(match_report_id)
    if not report:
        raise AppError(
            code="match_report_not_found",
            message="Match report was not found in the Phase 1A mock store.",
            status_code=404,
            details={"match_report_id": match_report_id},
        )
    return {"data": report, "request_id": request.state.request_id}
