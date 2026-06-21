from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.repositories import job_repository
from app.schemas.jobs import JobCreateRequest, JobProfile, JobRecord


MIN_JD_TEXT_LENGTH = 20


def validate_job_description(raw_text: str) -> None:
    if len(raw_text.strip()) < MIN_JD_TEXT_LENGTH:
        raise AppError(
            code="job_description_too_short",
            message="JD raw_text is too short for Phase 1 mock extraction.",
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
    return ["Mock responsibility extracted from JD text for Phase 1."]


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


def create_job(db: Session, payload: JobCreateRequest) -> JobRecord:
    validate_job_description(payload.raw_text)
    profile = build_mock_job_profile("pending", payload)
    return job_repository.create_job_with_profile(db, payload=payload, profile=profile)


def list_jobs(db: Session) -> list[JobRecord]:
    return job_repository.list_jobs(db)


def get_job(db: Session, jd_id: str) -> JobRecord:
    return job_repository.get_job(db, jd_id)
