from app.repositories.job_repository import create_job_with_profile, get_job, list_jobs
from app.schemas.jobs import JobCreateRequest, JobProfile


def test_job_repository_create_list_get(db_session):
    payload = JobCreateRequest(
        company="Repo Company",
        job_title="Backend Engineer",
        location="Sydney",
        raw_text="Build Python FastAPI services.",
        source_url=None,
    )
    profile = JobProfile(
        job_profile_id="ignored",
        role_category="Python Backend Developer",
        required_skills=["Python", "FastAPI"],
        preferred_skills=[],
        responsibilities=["Build services"],
        interview_focus=["API design"],
        risk_level="low",
        summary="Repository test profile.",
    )

    created = create_job_with_profile(db_session, payload=payload, profile=profile)
    listed = list_jobs(db_session)
    fetched = get_job(db_session, created.jd_id)

    assert created.jd_id.startswith("jd_")
    assert [item.jd_id for item in listed] == [created.jd_id]
    assert fetched.company == "Repo Company"
    assert fetched.job_profile.required_skills == ["Python", "FastAPI"]
