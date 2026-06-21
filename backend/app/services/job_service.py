from app.core.errors import AppError
from app.schemas.jobs import JobCreateRequest, JobProfile, JobRecord
from app.services.mock_store import store


MIN_JD_TEXT_LENGTH = 20


def validate_job_description(raw_text: str) -> None:
    if len(raw_text.strip()) < MIN_JD_TEXT_LENGTH:
        raise AppError(
            code="job_description_too_short",
            message="JD raw_text is too short for Phase 1B mock extraction.",
            status_code=400,
            details={"min_length": MIN_JD_TEXT_LENGTH},
        )


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


def infer_role_category(job_title: str, raw_text: str) -> str:
    combined = f"{job_title} {raw_text}".lower()
    if "rag" in combined or "llm" in combined or "ai application" in combined:
        return "AI Application Engineer"
    if "backend" in combined or "fastapi" in combined:
        return "Python Backend Developer"
    if "frontend" in combined or "react" in combined:
        return "Frontend / Fullstack Developer"
    return job_title


def extract_responsibilities(raw_text: str) -> list[str]:
    sentences = [
        part.strip(" .")
        for part in raw_text.replace("\n", " ").split(".")
        if part.strip()
    ]
    if sentences:
        return [sentences[0]]
    return ["Mock responsibility extracted from JD text for Phase 1B."]


def build_mock_job_profile(jd_id: str, payload: JobCreateRequest) -> JobProfile:
    required_skills, preferred_skills = extract_mock_skills(payload.raw_text)
    role_category = infer_role_category(payload.job_title, payload.raw_text)
    return JobProfile(
        job_profile_id=f"profile_{jd_id}",
        role_category=role_category,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        responsibilities=extract_responsibilities(payload.raw_text),
        business_scenarios=[],
        hidden_requirements=[],
        interview_focus=[
            "Explain relevant project decisions with evidence.",
            "Discuss API design, reliability, and tradeoffs.",
        ],
        risk_level="low",
        summary="Deterministic mock job profile. No LLM parsing was used.",
    )


def create_mock_job(payload: JobCreateRequest) -> JobRecord:
    validate_job_description(payload.raw_text)
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
    return job


def list_mock_jobs() -> list[JobRecord]:
    return list(store.jobs.values())


def get_mock_job(jd_id: str) -> JobRecord:
    job = store.jobs.get(jd_id)
    if not job:
        raise AppError(
            code="job_not_found",
            message="JD was not found in the Phase 1B mock store.",
            status_code=404,
            details={"jd_id": jd_id},
        )
    return job
