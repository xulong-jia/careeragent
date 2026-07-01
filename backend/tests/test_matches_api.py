from conftest import get_data, get_error, make_client
from app.models.match import MatchReport as MatchReportModel
from app.models.resume import ResumeVersion


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
            "raw_text": "Must build Python FastAPI RAG services. React is preferred.",
            "source_url": None,
        },
    )
    return get_data(resume_response)["resume_id"], get_data(job_response)["jd_id"]


def create_job(
    client,
    title="AI Application Engineer",
    raw_text="Must build Python FastAPI RAG services. React is preferred.",
):
    response = client.post(
        "/api/jobs",
        json={
            "company": "Mock Company",
            "job_title": title,
            "location": "Shanghai",
            "raw_text": raw_text,
            "source_url": None,
        },
    )
    assert response.status_code == 201
    return get_data(response)["jd_id"]


def get_initial_version_id(client, resume_id):
    response = client.get(f"/api/resumes/{resume_id}/versions")
    assert response.status_code == 200
    data = get_data(response)
    assert data["total"] >= 1
    return data["items"][0]["resume_version_id"]


def test_match_run_returns_trustworthy_foundation_report():
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
    assert data["resume_version_id"].startswith(f"{resume_id}_version_")
    assert data["jd_id"] == jd_id
    assert data["job_profile_id"].startswith(f"profile_{jd_id}_")
    assert data["created_at"] is not None
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
    assert data["recommended_projects"] is not None
    assert data["score_breakdown"]["foundation_only"] is True
    assert data["scoring_method"] == "deterministic_trustworthy_match_v1"
    assert 0 < data["confidence"] <= 1
    assert data["dimension_scores"]["skill_match"] > 70


def test_match_run_with_resume_id_persists_report_to_db(db_session):
    client = make_client()
    resume_id, jd_id = create_resume_and_job(client)

    response = client.post(
        "/api/matches/run",
        json={"resume_id": resume_id, "jd_id": jd_id},
    )

    assert response.status_code == 201
    data = get_data(response)
    record = db_session.get(MatchReportModel, data["match_report_id"])
    assert record is not None
    assert record.resume_version_id == data["resume_version_id"]
    assert record.jd_id == jd_id
    assert record.job_profile_id == data["job_profile_id"]
    assert record.scoring_method == "deterministic_trustworthy_match_v1"
    assert isinstance(record.score_breakdown, dict)


def test_match_run_with_resume_version_id_persists_report_to_db(db_session):
    client = make_client()
    resume_id, jd_id = create_resume_and_job(client)
    version_id = get_initial_version_id(client, resume_id)

    response = client.post(
        "/api/matches/run",
        json={"resume_version_id": version_id, "jd_id": jd_id},
    )

    assert response.status_code == 201
    data = get_data(response)
    assert data["resume_id"] == resume_id
    assert data["resume_version_id"] == version_id
    assert db_session.get(MatchReportModel, data["match_report_id"]) is not None


def test_match_run_rejects_missing_resume():
    client = make_client()
    _, jd_id = create_resume_and_job(client)

    response = client.post(
        "/api/matches/run",
        json={"resume_id": "resume_missing", "jd_id": jd_id},
    )

    assert response.status_code == 404
    assert get_error(response)["code"] == "resume_not_found"


def test_match_run_rejects_missing_resume_version():
    client = make_client()
    _, jd_id = create_resume_and_job(client)

    response = client.post(
        "/api/matches/run",
        json={"resume_version_id": "missing_version", "jd_id": jd_id},
    )

    assert response.status_code == 404
    assert get_error(response)["code"] == "resume_version_not_found"


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

    response = client.post("/api/matches/run", json={"jd_id": "jd_0001"})

    assert response.status_code == 422
    assert get_error(response)["code"] == "validation_error"


def test_match_run_rejects_resume_version_mismatch():
    client = make_client()
    resume_id, jd_id = create_resume_and_job(client)
    other_resume_response = client.post(
        "/api/resumes/upload",
        files={
            "file": (
                "other.md",
                b"React frontend project experience.",
                "text/markdown",
            )
        },
    )
    other_resume_id = get_data(other_resume_response)["resume_id"]
    other_version_id = get_initial_version_id(client, other_resume_id)

    response = client.post(
        "/api/matches/run",
        json={
            "resume_id": resume_id,
            "resume_version_id": other_version_id,
            "jd_id": jd_id,
        },
    )

    assert response.status_code == 400
    assert get_error(response)["code"] == "resume_version_mismatch"


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


def test_match_list_filters_by_jd_and_resume_version():
    client = make_client()
    resume_id, jd_id = create_resume_and_job(client)
    version_id = get_initial_version_id(client, resume_id)
    other_jd_id = create_job(
        client,
        title="Backend Engineer",
        raw_text="Python SQL backend platform service ownership.",
    )
    first = client.post(
        "/api/matches/run",
        json={"resume_version_id": version_id, "jd_id": jd_id},
    )
    second = client.post(
        "/api/matches/run",
        json={"resume_version_id": version_id, "jd_id": other_jd_id},
    )
    first_id = get_data(first)["match_report_id"]
    second_id = get_data(second)["match_report_id"]

    by_jd = get_data(client.get(f"/api/matches?jd_id={jd_id}"))
    by_version = get_data(client.get(f"/api/matches?resume_version_id={version_id}"))
    by_both = get_data(
        client.get(f"/api/matches?jd_id={jd_id}&resume_version_id={version_id}")
    )

    assert [item["match_report_id"] for item in by_jd["items"]] == [first_id]
    assert {item["match_report_id"] for item in by_version["items"]} == {
        first_id,
        second_id,
    }
    assert [item["match_report_id"] for item in by_both["items"]] == [first_id]


def test_same_jd_can_match_multiple_resume_versions():
    client = make_client()
    resume_id, jd_id = create_resume_and_job(client)
    initial_version_id = get_initial_version_id(client, resume_id)
    clone_response = client.post(
        f"/api/resume-versions/{initial_version_id}/clone",
        json={"version_name": "Backend version", "target_role": "Backend Engineer"},
    )
    clone_version_id = get_data(clone_response)["resume_version_id"]

    first = client.post(
        "/api/matches/run",
        json={"resume_version_id": initial_version_id, "jd_id": jd_id},
    )
    second = client.post(
        "/api/matches/run",
        json={"resume_version_id": clone_version_id, "jd_id": jd_id},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    reports = get_data(client.get(f"/api/matches?jd_id={jd_id}"))
    assert reports["total"] == 2
    assert {
        item["resume_version_id"] for item in reports["items"]
    } == {initial_version_id, clone_version_id}


def test_match_compare_sorts_multiple_resume_versions_for_same_jd():
    client = make_client()
    resume_id, jd_id = create_resume_and_job(client)
    initial_version_id = get_initial_version_id(client, resume_id)
    weak_resume_response = client.post(
        "/api/resumes/upload",
        files={
            "file": (
                "weak.md",
                b"React TypeScript frontend dashboard project.",
                "text/markdown",
            )
        },
    )
    weak_version_id = get_initial_version_id(
        client, get_data(weak_resume_response)["resume_id"]
    )

    response = client.post(
        "/api/matches/compare",
        json={
            "jd_id": jd_id,
            "resume_version_ids": [initial_version_id, weak_version_id],
        },
    )

    assert response.status_code == 200
    data = get_data(response)
    assert data["compare_mode"] == "same_jd_multiple_resumes"
    assert [item["rank"] for item in data["items"]] == [1, 2]
    assert data["items"][0]["total_score"] >= data["items"][1]["total_score"]
    assert data["items"][0]["score_delta_from_top"] == 0


def test_match_compare_sorts_multiple_jds_for_same_resume_version():
    client = make_client()
    resume_id, jd_id = create_resume_and_job(client)
    version_id = get_initial_version_id(client, resume_id)
    weak_jd_id = create_job(
        client,
        title="Frontend Engineer",
        raw_text="React TypeScript dashboard UI role.",
    )

    response = client.post(
        "/api/matches/compare",
        json={"resume_version_id": version_id, "jd_ids": [jd_id, weak_jd_id]},
    )

    assert response.status_code == 200
    data = get_data(response)
    assert data["compare_mode"] == "same_resume_multiple_jds"
    assert {item["jd_id"] for item in data["items"]} == {jd_id, weak_jd_id}
    assert data["items"][0]["total_score"] >= data["items"][1]["total_score"]


def test_same_resume_version_can_match_multiple_jobs():
    client = make_client()
    resume_id, jd_id = create_resume_and_job(client)
    version_id = get_initial_version_id(client, resume_id)
    other_jd_id = create_job(
        client,
        title="Platform Engineer",
        raw_text="Docker SQL platform reliability engineering role.",
    )

    first = client.post(
        "/api/matches/run",
        json={"resume_version_id": version_id, "jd_id": jd_id},
    )
    second = client.post(
        "/api/matches/run",
        json={"resume_version_id": version_id, "jd_id": other_jd_id},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    reports = get_data(client.get(f"/api/matches?resume_version_id={version_id}"))
    assert reports["total"] == 2
    assert {item["jd_id"] for item in reports["items"]} == {jd_id, other_jd_id}


def test_archived_version_is_not_selected_by_resume_id_but_can_be_explicit():
    client = make_client()
    resume_id, jd_id = create_resume_and_job(client)
    version_id = get_initial_version_id(client, resume_id)
    archive_response = client.patch(f"/api/resume-versions/{version_id}/archive")
    assert archive_response.status_code == 200

    default_response = client.post(
        "/api/matches/run",
        json={"resume_id": resume_id, "jd_id": jd_id},
    )
    explicit_response = client.post(
        "/api/matches/run",
        json={"resume_version_id": version_id, "jd_id": jd_id},
    )

    assert default_response.status_code == 404
    assert get_error(default_response)["code"] == "resume_version_not_found"
    assert explicit_response.status_code == 201
    assert get_data(explicit_response)["resume_version_id"] == version_id


def test_match_report_persists_across_new_db_session(db_session):
    client = make_client()
    resume_id, jd_id = create_resume_and_job(client)
    response = client.post(
        "/api/matches/run",
        json={"resume_id": resume_id, "jd_id": jd_id},
    )
    match_report_id = get_data(response)["match_report_id"]

    db_session.expire_all()
    persisted = db_session.get(MatchReportModel, match_report_id)

    assert persisted is not None
    assert persisted.jd_id == jd_id
    assert db_session.get(ResumeVersion, persisted.resume_version_id) is not None
