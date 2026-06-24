import re

from conftest import get_data, get_error, make_client


APPLICATION_ID_PATTERN = re.compile(r"^app_[0-9a-f]{12}$")

PRIVATE_TEXT_KEYS = {
    "raw_text",
    "jd_raw_text",
    "resume_text",
    "job_text",
    "chunk_text",
    "full_text",
}


def _assert_private_safe(value):
    if isinstance(value, dict):
        assert PRIVATE_TEXT_KEYS.isdisjoint(value.keys())
        for child in value.values():
            _assert_private_safe(child)
    elif isinstance(value, list):
        for child in value:
            _assert_private_safe(child)


def _create_resume_job_and_match(client):
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
    assert resume_response.status_code == 201
    resume_id = get_data(resume_response)["resume_id"]

    versions_response = client.get(f"/api/resumes/{resume_id}/versions")
    assert versions_response.status_code == 200
    resume_version_id = get_data(versions_response)["items"][0]["resume_version_id"]

    job_response = client.post(
        "/api/jobs",
        json={
            "company": "Synthetic Company",
            "job_title": "AI Application Engineer",
            "location": "Shanghai",
            "raw_text": "Python FastAPI RAG React platform role.",
            "source_url": None,
        },
    )
    assert job_response.status_code == 201
    jd_id = get_data(job_response)["jd_id"]

    match_response = client.post(
        "/api/matches/run",
        json={"resume_version_id": resume_version_id, "jd_id": jd_id},
    )
    assert match_response.status_code == 201
    match_report_id = get_data(match_response)["match_report_id"]

    return {
        "jd_id": jd_id,
        "resume_version_id": resume_version_id,
        "match_report_id": match_report_id,
    }


def _application_payload(**overrides):
    payload = {
        "company": "Synthetic Company",
        "role_title": "AI Application Engineer",
        "role_category": "AI Application",
        "status": "saved",
        "apply_date": "2026-06-20",
        "next_step_date": "2026-06-30",
        "interview_notes": "Short synthetic interview note.",
        "reflection": "Short synthetic reflection.",
        "tags": ["synthetic", "priority"],
    }
    payload.update(overrides)
    return payload


def _create_application(client, **overrides):
    response = client.post("/api/applications", json=_application_payload(**overrides))
    assert response.status_code == 201
    return get_data(response)


def test_create_application_record_with_optional_refs_and_safe_response():
    client = make_client()
    refs = _create_resume_job_and_match(client)

    data = _create_application(client, **refs)

    assert APPLICATION_ID_PATTERN.match(data["application_id"])
    assert data["company"] == "Synthetic Company"
    assert data["role_title"] == "AI Application Engineer"
    assert data["role_category"] == "AI Application"
    assert data["jd_id"] == refs["jd_id"]
    assert data["resume_version_id"] == refs["resume_version_id"]
    assert data["match_report_id"] == refs["match_report_id"]
    assert data["status"] == "saved"
    assert data["apply_date"] == "2026-06-20"
    assert data["next_step_date"] == "2026-06-30"
    assert data["tags"] == ["synthetic", "priority"]
    assert data["created_at"]
    assert data["updated_at"]
    _assert_private_safe(data)


def test_create_multiple_applications_generates_unique_stable_ids():
    client = make_client()

    applications = [
        _create_application(client, company=f"Synthetic Company {index}")
        for index in range(5)
    ]
    application_ids = [application["application_id"] for application in applications]

    assert len(application_ids) == len(set(application_ids))
    assert all(
        APPLICATION_ID_PATTERN.match(application_id)
        for application_id in application_ids
    )


def test_create_application_record_without_refs_supports_manual_tracking():
    client = make_client()

    data = _create_application(
        client,
        jd_id=None,
        resume_version_id=None,
        match_report_id=None,
        status="ready_to_apply",
    )

    assert data["jd_id"] is None
    assert data["resume_version_id"] is None
    assert data["match_report_id"] is None
    assert data["status"] == "ready_to_apply"


def test_list_application_records_and_detail():
    client = make_client()
    first = _create_application(client, company="Alpha Labs")
    second = _create_application(client, company="Beta Labs", status="applied")

    list_response = client.get("/api/applications")
    detail_response = client.get(f"/api/applications/{first['application_id']}")

    assert list_response.status_code == 200
    listed = get_data(list_response)
    assert listed["total"] == 2
    assert {item["application_id"] for item in listed["items"]} == {
        first["application_id"],
        second["application_id"],
    }
    assert detail_response.status_code == 200
    assert get_data(detail_response)["application_id"] == first["application_id"]


def test_update_application_status_and_notes():
    client = make_client()
    created = _create_application(client)

    response = client.patch(
        f"/api/applications/{created['application_id']}",
        json={
            "status": "first_interview",
            "next_step_date": "2026-07-03",
            "interview_notes": "Updated short interview summary.",
            "reflection": "Updated short reflection.",
            "tags": ["interview"],
        },
    )

    assert response.status_code == 200
    data = get_data(response)
    assert data["status"] == "first_interview"
    assert data["next_step_date"] == "2026-07-03"
    assert data["interview_notes"] == "Updated short interview summary."
    assert data["reflection"] == "Updated short reflection."
    assert data["tags"] == ["interview"]


def test_list_applications_supports_basic_filters():
    client = make_client()
    refs = _create_resume_job_and_match(client)
    target = _create_application(
        client,
        company="Target Company",
        role_category="AI Application",
        status="applied",
        **refs,
    )
    _create_application(
        client,
        company="Other Company",
        role_category="Backend",
        status="saved",
    )

    filter_cases = [
        {"status": "applied"},
        {"company": "Target"},
        {"role_category": "AI Application"},
        {"resume_version_id": refs["resume_version_id"]},
        {"jd_id": refs["jd_id"]},
    ]
    for params in filter_cases:
        response = client.get("/api/applications", params=params)
        assert response.status_code == 200
        data = get_data(response)
        assert [item["application_id"] for item in data["items"]] == [
            target["application_id"]
        ]


def test_application_stats_counts_status_buckets():
    client = make_client()
    _create_application(client, status="saved")
    _create_application(client, status="first_interview")
    _create_application(client, status="second_interview")
    _create_application(client, status="offer")
    _create_application(client, status="rejected")
    _create_application(client, status="withdrawn")

    response = client.get("/api/applications/stats")

    assert response.status_code == 200
    data = get_data(response)
    assert data["total_applications"] == 6
    assert data["by_status"]["saved"] == 1
    assert data["by_status"]["first_interview"] == 1
    assert data["by_status"]["second_interview"] == 1
    assert data["interview_count"] == 2
    assert data["offer_count"] == 1
    assert data["rejected_count"] == 1
    assert data["active_count"] == 3


def test_application_rejects_invalid_status():
    client = make_client()

    create_response = client.post(
        "/api/applications",
        json=_application_payload(status="sent"),
    )
    assert create_response.status_code == 400
    assert get_error(create_response)["code"] == "application_invalid_field"

    created = _create_application(client)
    patch_response = client.patch(
        f"/api/applications/{created['application_id']}",
        json={"status": "closed"},
    )
    assert patch_response.status_code == 400
    assert get_error(patch_response)["code"] == "application_invalid_field"


def test_application_rejects_missing_optional_refs_when_provided():
    client = make_client()

    invalid_cases = [
        ("jd_id", "missing_jd", "job_not_found"),
        ("resume_version_id", "missing_version", "resume_version_not_found"),
        ("match_report_id", "missing_match", "match_report_not_found"),
    ]
    for field, value, expected_code in invalid_cases:
        response = client.post(
            "/api/applications",
            json=_application_payload(**{field: value}),
        )
        assert response.status_code == 404
        assert get_error(response)["code"] == expected_code


def test_application_response_does_not_include_resume_or_jd_raw_text():
    client = make_client()
    refs = _create_resume_job_and_match(client)
    created = _create_application(client, **refs)

    detail_response = client.get(f"/api/applications/{created['application_id']}")
    list_response = client.get("/api/applications")
    stats_response = client.get("/api/applications/stats")

    assert detail_response.status_code == 200
    assert list_response.status_code == 200
    assert stats_response.status_code == 200
    _assert_private_safe(get_data(detail_response))
    _assert_private_safe(get_data(list_response))
    _assert_private_safe(get_data(stats_response))
