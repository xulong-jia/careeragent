from datetime import date, timedelta
import re

from app.models.agent import AgentRun
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
        "source_url": "https://example.com/jobs/ai-application-engineer",
        "location": "Shanghai",
        "priority": "high",
        "notes": "Short synthetic operations note.",
        "interview_notes": "Short synthetic interview note.",
        "reflection": "Short synthetic reflection.",
        "interview_question_ids": ["iq_synthetic_001"],
        "last_contact_date": "2026-06-21",
        "tags": ["synthetic", "priority"],
    }
    payload.update(overrides)
    return payload


def _create_application(client, **overrides):
    if not any(
        field in overrides
        for field in ("jd_id", "resume_version_id", "match_report_id")
    ):
        overrides = {**_create_resume_job_and_match(client), **overrides}
    response = client.post("/api/applications", json=_application_payload(**overrides))
    assert response.status_code == 201
    return get_data(response)


def test_create_application_record_with_required_refs_and_safe_response():
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
    assert data["source_url"] == "https://example.com/jobs/ai-application-engineer"
    assert data["location"] == "Shanghai"
    assert data["priority"] == "high"
    assert data["notes"] == "Short synthetic operations note."
    assert data["interview_question_ids"] == ["iq_synthetic_001"]
    assert data["last_contact_date"] == "2026-06-21"
    assert data["tags"] == ["synthetic", "priority"]
    assert data["status_history"][0]["from_status"] is None
    assert data["status_history"][0]["to_status"] == "saved"
    assert data["status_history"][0]["reason"] == "created"
    assert data["created_at"]
    assert data["updated_at"]
    _assert_private_safe(data)


def test_create_application_record_with_agent_run_link(db_session):
    client = make_client()
    refs = _create_resume_job_and_match(client)
    run = AgentRun(
        id="agent_run_application_0001",
        workflow_name="job_application_preparation",
        status="completed",
        input_refs={},
        output_refs={},
    )
    db_session.add(run)
    db_session.commit()

    data = _create_application(client, **refs, agent_run_id=run.id)
    list_response = client.get("/api/applications", params={"agent_run_id": run.id})

    assert data["agent_run_id"] == run.id
    assert list_response.status_code == 200
    listed = get_data(list_response)
    assert [item["application_id"] for item in listed["items"]] == [
        data["application_id"]
    ]


def test_create_multiple_applications_generates_unique_stable_ids():
    client = make_client()
    refs = _create_resume_job_and_match(client)

    applications = [
        _create_application(client, company=f"Synthetic Company {index}", **refs)
        for index in range(5)
    ]
    application_ids = [application["application_id"] for application in applications]

    assert len(application_ids) == len(set(application_ids))
    assert all(
        APPLICATION_ID_PATTERN.match(application_id)
        for application_id in application_ids
    )


def test_create_application_requires_jd_and_resume_version_refs():
    client = make_client()

    missing_jd_response = client.post(
        "/api/applications",
        json=_application_payload(status="ready_to_apply"),
    )
    assert missing_jd_response.status_code == 400
    missing_jd_error = get_error(missing_jd_response)
    assert missing_jd_error["code"] == "application_invalid_field"
    assert missing_jd_error["details"]["field"] == "jd_id"

    refs = _create_resume_job_and_match(client)
    missing_resume_response = client.post(
        "/api/applications",
        json=_application_payload(
            jd_id=refs["jd_id"],
            resume_version_id=None,
            match_report_id=None,
        ),
    )
    assert missing_resume_response.status_code == 400
    missing_resume_error = get_error(missing_resume_response)
    assert missing_resume_error["code"] == "application_invalid_field"
    assert missing_resume_error["details"]["field"] == "resume_version_id"


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
            "status_reason": "interview_invited",
            "status_note": "Recruiter scheduled first interview.",
            "next_step_date": "2026-07-03",
            "source_url": "https://example.com/jobs/updated",
            "location": "Remote",
            "priority": "medium",
            "notes": "Updated operations note.",
            "interview_notes": "Updated short interview summary.",
            "reflection": "Updated short reflection.",
            "interview_question_ids": ["iq_synthetic_002"],
            "last_contact_date": "2026-07-01",
            "tags": ["interview"],
        },
    )

    assert response.status_code == 200
    data = get_data(response)
    assert data["status"] == "first_interview"
    assert data["next_step_date"] == "2026-07-03"
    assert data["source_url"] == "https://example.com/jobs/updated"
    assert data["location"] == "Remote"
    assert data["priority"] == "medium"
    assert data["notes"] == "Updated operations note."
    assert data["interview_notes"] == "Updated short interview summary."
    assert data["reflection"] == "Updated short reflection."
    assert data["interview_question_ids"] == ["iq_synthetic_002"]
    assert data["last_contact_date"] == "2026-07-01"
    assert data["tags"] == ["interview"]
    assert data["status_history"][-1]["from_status"] == "saved"
    assert data["status_history"][-1]["to_status"] == "first_interview"
    assert data["status_history"][-1]["reason"] == "interview_invited"
    assert data["status_history"][-1]["note"] == "Recruiter scheduled first interview."


def test_application_status_history_endpoint_and_no_duplicate_for_non_status_patch():
    client = make_client()
    created = _create_application(client)

    status_response = client.patch(
        f"/api/applications/{created['application_id']}",
        json={"status": "applied", "status_reason": "submitted"},
    )
    non_status_response = client.patch(
        f"/api/applications/{created['application_id']}",
        json={"notes": "Changed note without changing status."},
    )
    history_response = client.get(
        f"/api/applications/{created['application_id']}/status-history"
    )

    assert status_response.status_code == 200
    assert non_status_response.status_code == 200
    assert history_response.status_code == 200
    history = get_data(history_response)
    assert history["total"] == 2
    assert [item["to_status"] for item in history["items"]] == ["saved", "applied"]
    assert history["items"][1]["reason"] == "submitted"


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
        priority="low",
        status="saved",
    )

    filter_cases = [
        {"status": "applied"},
        {"company": "Target"},
        {"role_category": "AI Application"},
        {"resume_version_id": refs["resume_version_id"]},
        {"jd_id": refs["jd_id"]},
        {"match_report_id": refs["match_report_id"]},
        {"priority": "high"},
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
    refs = _create_resume_job_and_match(client)
    _create_application(client, status="saved", **refs)
    _create_application(client, status="first_interview", **refs)
    _create_application(client, status="second_interview", **refs)
    _create_application(client, status="offer", **refs)
    _create_application(client, status="rejected", **refs)
    _create_application(client, status="withdrawn", **refs)

    response = client.get("/api/applications/stats")

    assert response.status_code == 200
    data = get_data(response)
    assert data["total"] == 6
    assert data["total_applications"] == 6
    assert data["by_status"]["saved"] == 1
    assert data["by_status"]["first_interview"] == 1
    assert data["by_status"]["second_interview"] == 1
    assert data["interview_count"] == 2
    assert data["offer_count"] == 1
    assert data["rejected_count"] == 1
    assert data["withdrawn_count"] == 1
    assert data["active_count"] == 3
    assert data["conversion"]["applied_to_interview_rate"] == 0.4
    assert data["conversion"]["interview_to_offer_rate"] == 0.5
    assert data["conversion"]["applied_to_offer_rate"] == 0.2
    assert len(data["latest_applications"]) == 5


def test_application_stats_returns_upcoming_and_overdue_counts():
    client = make_client()
    refs = _create_resume_job_and_match(client)
    today = date.today()
    _create_application(
        client,
        status="saved",
        next_step_date=(today - timedelta(days=1)).isoformat(),
        **refs,
    )
    _create_application(
        client,
        status="applied",
        next_step_date=(today + timedelta(days=3)).isoformat(),
        **refs,
    )
    _create_application(
        client,
        status="first_interview",
        next_step_date=(today + timedelta(days=5)).isoformat(),
        **refs,
    )
    _create_application(
        client,
        status="offer",
        next_step_date=(today - timedelta(days=3)).isoformat(),
        **refs,
    )

    response = client.get("/api/applications/stats")

    assert response.status_code == 200
    data = get_data(response)
    assert data["upcoming_count"] == 2
    assert data["overdue_count"] == 1


def test_application_rejects_invalid_status():
    client = make_client()
    refs = _create_resume_job_and_match(client)

    create_response = client.post(
        "/api/applications",
        json=_application_payload(status="sent", **refs),
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


def test_application_reflection_endpoint_updates_reflection_without_status_history():
    client = make_client()
    created = _create_application(client)

    response = client.post(
        f"/api/applications/{created['application_id']}/reflection",
        json={
            "reflection": "Need stronger system design story.",
            "interview_notes": "Interviewer focused on FastAPI tradeoffs.",
            "failure_reason": "Weak project metrics.",
            "preparation_gaps": ["metrics", "deployment"],
            "next_actions": ["rewrite STAR examples"],
            "weakness_tags": ["system-design", "metrics"],
            "note": "Keep this as application reflection only.",
        },
    )

    assert response.status_code == 200
    data = get_data(response)
    assert data["interview_notes"] == "Interviewer focused on FastAPI tradeoffs."
    assert "Need stronger system design story." in data["reflection"]
    assert "Failure reason: Weak project metrics." in data["reflection"]
    assert "Preparation gaps: metrics, deployment" in data["reflection"]
    assert "Next actions: rewrite STAR examples" in data["reflection"]
    assert set(data["tags"]) == {
        "synthetic",
        "priority",
        "system-design",
        "metrics",
    }
    assert len(data["status_history"]) == 1


def test_application_rejects_missing_optional_refs_when_provided():
    client = make_client()

    invalid_cases = [
        ("jd_id", "missing_jd", "job_not_found"),
        ("resume_version_id", "missing_version", "resume_version_not_found"),
        ("match_report_id", "missing_match", "match_report_not_found"),
        ("agent_run_id", "missing_agent_run", "agent_run_not_found"),
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
