from conftest import get_data, get_error, make_client


def test_job_create_returns_mock_profile():
    client = make_client()

    response = client.post(
        "/api/jobs",
        json={
            "company": "Mock Company",
            "job_title": "AI Application Engineer",
            "location": "Shanghai",
            "raw_text": "We need Python, FastAPI, RAG experience. React is a plus.",
            "source_url": "https://example.com/job",
        },
    )

    assert response.status_code == 201
    data = get_data(response)
    assert data["jd_id"].startswith("jd_")
    assert data["company"] == "Mock Company"
    assert data["job_profile"]["role_category"] == "AI Application Engineer"
    assert "Python" in data["job_profile"]["required_skills"]
    assert "React" in data["job_profile"]["preferred_skills"]
    assert data["job_profile"]["responsibilities"]
    assert data["job_profile"]["interview_focus"]


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
    assert any(item["jd_id"] == jd_id for item in get_data(list_response)["items"])
    assert detail_response.status_code == 200
    assert get_data(detail_response)["jd_id"] == jd_id
