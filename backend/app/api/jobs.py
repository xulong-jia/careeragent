from fastapi import APIRouter, Request, status

from app.core.errors import AppError
from app.schemas.common import ApiResponse, ListResponse
from app.schemas.jobs import JobCreateRequest, JobProfile, JobRecord
from app.services.mock_store import store


router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def extract_mock_skills(raw_text: str) -> tuple[list[str], list[str]]:
    text = raw_text.lower()
    required_candidates = {
        "Python": "python",
        "FastAPI": "fastapi",
        "RAG": "rag",
        "SQL": "sql",
        "TypeScript": "typescript",
    }
    preferred_candidates = {
        "React": "react",
        "Docker": "docker",
        "LLM": "llm",
        "Vector Search": "vector",
    }
    required = [
        skill for skill, keyword in required_candidates.items() if keyword in text
    ]
    preferred = [
        skill for skill, keyword in preferred_candidates.items() if keyword in text
    ]
    return required, preferred


def build_mock_job_profile(jd_id: str, payload: JobCreateRequest) -> JobProfile:
    required_skills, preferred_skills = extract_mock_skills(payload.raw_text)
    return JobProfile(
        job_profile_id=f"profile_{jd_id}",
        role_category=payload.job_title,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        responsibilities=[
            "Mock responsibility extracted from JD text for Phase 1A.",
        ],
        business_scenarios=[],
        hidden_requirements=[],
        interview_focus=[
            "Explain relevant project decisions with evidence.",
            "Discuss backend API design and reliability tradeoffs.",
        ],
        risk_level="low",
        summary="Mock job profile placeholder. No LLM parsing was used.",
    )


@router.post("", response_model=ApiResponse[JobRecord], status_code=status.HTTP_201_CREATED)
async def create_job(
    request: Request, payload: JobCreateRequest
) -> dict[str, object]:
    jd_id = store.next_id("jd", len(store.jobs))
    profile = build_mock_job_profile(jd_id, payload)
    job = JobRecord(
        jd_id=jd_id,
        company=payload.company,
        job_title=payload.job_title,
        location=payload.location,
        raw_text=payload.raw_text,
        source_url=str(payload.source_url) if payload.source_url else None,
        job_profile=profile,
    )
    store.jobs[job.jd_id] = job
    return {"data": job, "request_id": request.state.request_id}


@router.get("", response_model=ApiResponse[ListResponse[JobRecord]])
async def list_jobs(request: Request) -> dict[str, object]:
    items = list(store.jobs.values())
    return {
        "data": ListResponse(items=items, total=len(items)),
        "request_id": request.state.request_id,
    }


@router.get("/{jd_id}", response_model=ApiResponse[JobRecord])
async def get_job(request: Request, jd_id: str) -> dict[str, object]:
    job = store.jobs.get(jd_id)
    if not job:
        raise AppError(
            code="job_not_found",
            message="JD was not found in the Phase 1A mock store.",
            status_code=404,
            details={"jd_id": jd_id},
        )
    return {"data": job, "request_id": request.state.request_id}
