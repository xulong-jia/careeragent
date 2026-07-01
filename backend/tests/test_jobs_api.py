from conftest import get_data, get_error, make_client
from app.models.job import JobDescription, JobProfile


def test_job_create_returns_parser_foundation_profile():
    client = make_client()

    response = client.post(
        "/api/jobs",
        json={
            "company": "Mock Company",
            "job_title": "AI Application Engineer",
            "location": "Shanghai",
            "raw_text": (
                "Must build RAG services with Python and FastAPI. "
                "Responsibilities include citation checks and API reliability. "
                "React is a plus."
            ),
            "source_url": "https://example.com/job",
        },
    )

    assert response.status_code == 201
    data = get_data(response)
    assert data["jd_id"].startswith("jd_")
    assert data["company"] == "Mock Company"
    assert "raw_text" not in data
    assert data["raw_text_preview"].startswith(
        "Must build RAG services with Python and FastAPI."
    )
    assert data["raw_text_preview"].endswith("...")
    assert data["job_profile"]["role_category"] == "AI Application Engineer"
    assert "Python" in data["job_profile"]["required_skills"]
    assert "React" in data["job_profile"]["preferred_skills"]
    assert data["job_profile"]["responsibilities"]
    assert data["job_profile"]["interview_focus"]
    assert data["job_profile"]["parse_confidence"] > 0
    assert data["job_profile"]["evidence"]
    assert data["job_profile"]["parser_metadata"]["foundation_only"] is True


def test_job_create_rejects_empty_raw_text():
    client = make_client()

    response = client.post(
        "/api/jobs",
        json={
            "company": "Mock Company",
            "job_title": "Backend Engineer",
            "location": "Sydney",
            "raw_text": "",
            "source_url": None,
        },
    )

    assert response.status_code == 422
    assert get_error(response)["code"] == "validation_error"


def test_job_create_rejects_too_short_raw_text():
    client = make_client()

    response = client.post(
        "/api/jobs",
        json={
            "company": "Mock Company",
            "job_title": "Backend Engineer",
            "location": "Sydney",
            "raw_text": "Python",
            "source_url": None,
        },
    )

    assert response.status_code == 400
    assert get_error(response)["code"] == "job_description_too_short"


def test_job_create_rejects_invalid_source_url():
    client = make_client()

    response = client.post(
        "/api/jobs",
        json={
            "company": "Mock Company",
            "job_title": "Backend Engineer",
            "location": "Sydney",
            "raw_text": "Build backend APIs with Python and FastAPI for internal tools.",
            "source_url": "not-a-url",
        },
    )

    assert response.status_code == 422
    assert get_error(response)["code"] == "validation_error"


def test_job_create_extracts_role_category_from_title_and_skills_from_text():
    client = make_client()

    response = client.post(
        "/api/jobs",
        json={
            "company": "Mock Company",
            "job_title": "Backend Platform Engineer",
            "location": "Sydney",
            "raw_text": "Must build Python FastAPI services. Responsibilities include API reliability checks. Docker is a plus.",
            "source_url": None,
        },
    )

    assert response.status_code == 201
    profile = get_data(response)["job_profile"]
    assert profile["role_category"] == "Python Backend Developer"
    assert profile["required_skills"] == ["Python", "FastAPI"]
    assert profile["preferred_skills"] == ["Docker"]
    assert profile["responsibilities"]


def test_job_create_classifies_data_platform_without_backend_misclassification():
    client = make_client()

    response = client.post(
        "/api/jobs",
        json={
            "company": "Example Data Tools",
            "job_title": "Data Platform Engineer",
            "location": "Brisbane",
            "raw_text": (
                "Must own SQL data workflows and Python automation for analytics users. "
                "Responsibilities include data quality checks and backend service monitoring. "
                "Docker is a plus."
            ),
            "source_url": None,
        },
    )

    assert response.status_code == 201
    profile = get_data(response)["job_profile"]
    assert profile["role_category"] == "Data Platform Engineer"
    assert "Python" in profile["required_skills"]
    assert "SQL" in profile["required_skills"]
    assert "Docker" in profile["preferred_skills"]
    assert any(item["field"] == "role_category" for item in profile["evidence"])


def test_job_create_short_but_valid_jd_has_low_confidence_warning():
    client = make_client()

    response = client.post(
        "/api/jobs",
        json={
            "company": "Example Short",
            "job_title": "Backend API Developer",
            "location": "Remote",
            "raw_text": "Need Python API developer. Details TBD.",
            "source_url": None,
        },
    )

    assert response.status_code == 201
    profile = get_data(response)["job_profile"]
    assert profile["parse_confidence"] < 0.8
    assert "job_description_short_low_confidence" in profile["warnings"]


def test_job_list_and_detail_return_created_job():
    client = make_client()
    create = client.post(
        "/api/jobs",
        json={
            "company": "Mock Company",
            "job_title": "Backend Engineer",
            "location": "Sydney",
            "raw_text": "Build backend APIs with Python and FastAPI.",
            "source_url": None,
        },
    )
    jd_id = get_data(create)["jd_id"]

    list_response = client.get("/api/jobs")
    detail_response = client.get(f"/api/jobs/{jd_id}")

    assert list_response.status_code == 200
    list_items = get_data(list_response)["items"]
    assert any(item["jd_id"] == jd_id for item in list_items)
    assert all("raw_text" not in item for item in list_items)
    assert all("raw_text_preview" in item for item in list_items)
    assert detail_response.status_code == 200
    detail = get_data(detail_response)
    assert detail["jd_id"] == jd_id
    assert "raw_text" not in detail
    assert "raw_text_preview" in detail


def test_job_create_persists_job_description_and_profile(db_session):
    client = make_client()
    create = client.post(
        "/api/jobs",
        json={
            "company": "Persistent Company",
            "job_title": "Backend Engineer",
            "location": "Sydney",
            "raw_text": "Build backend APIs with Python and FastAPI.",
            "source_url": None,
        },
    )
    jd_id = get_data(create)["jd_id"]

    job = db_session.get(JobDescription, jd_id)
    profiles = (
        db_session.query(JobProfile)
        .filter(JobProfile.jd_id == jd_id)
        .all()
    )

    assert job is not None
    assert job.company == "Persistent Company"
    assert len(profiles) == 1
    assert profiles[0].profile_version == 1
    assert profiles[0].required_skills == ["Python", "FastAPI"]
    assert profiles[0].parse_confidence > 0
    assert profiles[0].evidence
