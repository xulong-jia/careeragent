from conftest import get_data, get_error, make_client


def create_resume_and_job(client):
    resume_response = client.post(
        "/api/resumes/upload",
        files={
            "file": (
                "resume.md",
                b"Python FastAPI React project experience.",
                "text/markdown",
            )
        },
    )
    job_response = client.post(
        "/api/jobs",
        json={
            "company": "Mock Company",
            "job_title": "AI Application Engineer",
            "location": "Shanghai",
            "raw_text": "Python FastAPI RAG React",
            "source_url": None,
        },
    )
    return get_data(resume_response)["resume_id"], get_data(job_response)["jd_id"]


def test_match_run_returns_mock_report():
    client = make_client()
    resume_id, jd_id = create_resume_and_job(client)

    response = client.post(
        "/api/matches/run",
        json={"resume_id": resume_id, "jd_id": jd_id},
    )

    assert response.status_code == 201
    data = get_data(response)
    assert data["match_report_id"].startswith("match_")
    assert data["resume_id"] == resume_id
    assert data["jd_id"] == jd_id
    assert isinstance(data["total_score"], int)
    assert set(data["dimension_scores"]) >= {
        "skill_match",
        "project_relevance",
        "business_understanding",
        "expression_quality",
        "education_fit",
        "risk_control",
    }
    assert data["evidence"]
    assert data["strengths"]
    assert data["gaps"]
    assert data["rewrite_priorities"]
    assert data["risk_flags"] == []
    assert data["dimension_scores"]["skill_match"] > 70


def test_match_run_rejects_missing_resume():
    client = make_client()
    _, jd_id = create_resume_and_job(client)

    response = client.post(
        "/api/matches/run",
        json={"resume_id": "resume_missing", "jd_id": jd_id},
    )

    assert response.status_code == 404
    assert get_error(response)["code"] == "resume_not_found"


def test_match_run_rejects_missing_job():
    client = make_client()
    resume_id, _ = create_resume_and_job(client)

    response = client.post(
        "/api/matches/run",
        json={"resume_id": resume_id, "jd_id": "jd_missing"},
    )

    assert response.status_code == 404
    assert get_error(response)["code"] == "job_not_found"


def test_match_run_rejects_missing_input_fields():
    client = make_client()

    response = client.post("/api/matches/run", json={"resume_id": ""})

    assert response.status_code == 422
    assert get_error(response)["code"] == "validation_error"


def test_match_list_and_detail_return_created_report():
    client = make_client()
    resume_id, jd_id = create_resume_and_job(client)
    run = client.post("/api/matches/run", json={"resume_id": resume_id, "jd_id": jd_id})
    match_report_id = get_data(run)["match_report_id"]

    list_response = client.get("/api/matches")
    detail_response = client.get(f"/api/matches/{match_report_id}")

    assert list_response.status_code == 200
    assert any(
        item["match_report_id"] == match_report_id
        for item in get_data(list_response)["items"]
    )
    assert detail_response.status_code == 200
    assert get_data(detail_response)["match_report_id"] == match_report_id
