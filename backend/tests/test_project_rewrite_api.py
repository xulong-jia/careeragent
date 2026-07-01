from conftest import get_data, get_error, make_client


PRIVATE_TEXT_KEYS = {
    "raw_text",
    "raw_text_preview",
    "resume_text",
    "full_text",
    "source_text",
}


def _assert_private_safe(value):
    if isinstance(value, dict):
        assert PRIVATE_TEXT_KEYS.isdisjoint(value.keys())
        for child in value.values():
            _assert_private_safe(child)
    elif isinstance(value, list):
        for child in value:
            _assert_private_safe(child)


def _create_project(client, **overrides):
    payload = {
        "name": "CareerAgent RAG Workbench",
        "role": "Backend Engineer",
        "period": "2026-02 to 2026-05",
        "background": "Synthetic local learning project for job preparation.",
        "tech_stack": ["Python", "FastAPI"],
        "responsibilities": [
            "Built FastAPI APIs for document indexing and search.",
            "Implemented deterministic retrieval workflow for project evidence.",
        ],
        "results": [
            "Reduced retrieval latency by 30% in local synthetic tests.",
        ],
        "evidence": [],
        "status": "active",
    }
    payload.update(overrides)
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 201
    return get_data(response)


def _create_job(client, raw_text: str | None = None):
    response = client.post(
        "/api/jobs",
        json={
            "company": "Synthetic AI Co",
            "job_title": "Backend AI Engineer",
            "location": "Shanghai",
            "raw_text": raw_text
            or (
                "We need Python FastAPI SQL backend skills. "
                "React and Docker are preferred for internal tooling."
            ),
            "source_url": None,
        },
    )
    assert response.status_code == 201
    return get_data(response)


def _create_profile(client):
    response = client.post(
        "/api/profiles",
        json={
            "target_roles": ["Backend AI Engineer"],
            "target_industries": ["Enterprise Software"],
            "target_locations": ["Shanghai"],
            "skill_map": {"backend": ["FastAPI"]},
            "preferences": {},
            "source_resume_version_id": None,
        },
    )
    assert response.status_code == 201
    return get_data(response)


def _create_resume_version(client, content: bytes = b"PRIVATE_RESUME_TEXT FastAPI"):
    response = client.post(
        "/api/resumes/upload",
        files={"file": ("project-rewrite-source.md", content, "text/markdown")},
    )
    assert response.status_code == 201
    resume_id = get_data(response)["resume_id"]
    versions_response = client.get(f"/api/resumes/{resume_id}/versions")
    assert versions_response.status_code == 200
    return get_data(versions_response)["items"][0]["resume_version_id"]


def _create_match_report(client, resume_version_id: str, jd_id: str):
    response = client.post(
        "/api/matches/run",
        json={"resume_version_id": resume_version_id, "jd_id": jd_id},
    )
    assert response.status_code == 201
    return get_data(response)


def test_create_project_rewrite_success_and_get_detail():
    client = make_client()
    project = _create_project(client)
    job = _create_job(client)

    response = client.post(
        f"/api/projects/{project['id']}/rewrite",
        json={"jd_id": job["jd_id"]},
    )

    assert response.status_code == 201
    data = get_data(response)
    assert data["id"].startswith("project_rewrite_")
    assert data["project_id"] == project["id"]
    assert data["jd_id"] == job["jd_id"]
    assert data["rewrite_strategy"] == "deterministic_trustworthy_project_rewrite_v1"
    assert data["rewrite_method"] == "deterministic_trustworthy_project_rewrite_v1"
    assert 0 < data["confidence"] <= 1
    assert "FastAPI" in {point["skill"] for point in data["matched_points"]}
    assert data["rewritten_bullets"]
    assert {
        "before",
        "after",
        "reason",
        "evidence_required",
        "forbidden_changes",
        "matched_jd_requirements",
        "missing_points",
        "risk_level",
        "confidence",
    }.issubset(data["rewritten_bullets"][0])
    assert data["forbidden_changes"]
    _assert_private_safe(data)

    detail_response = client.get(f"/api/project-rewrites/{data['id']}")
    assert detail_response.status_code == 200
    detail = get_data(detail_response)
    assert detail["id"] == data["id"]
    assert detail["matched_points"] == data["matched_points"]


def test_project_rewrite_missing_required_records_return_errors():
    client = make_client()
    project = _create_project(client)
    job = _create_job(client)

    missing_project = client.post(
        "/api/projects/missing_project/rewrite",
        json={"jd_id": job["jd_id"]},
    )
    missing_job = client.post(
        f"/api/projects/{project['id']}/rewrite",
        json={"jd_id": "missing_jd"},
    )

    assert missing_project.status_code == 404
    assert get_error(missing_project)["code"] == "project_not_found"
    assert missing_job.status_code == 404
    assert get_error(missing_job)["code"] == "job_not_found"


def test_project_rewrite_missing_optional_refs_return_errors():
    client = make_client()
    project = _create_project(client)
    job = _create_job(client)

    missing_resume = client.post(
        f"/api/projects/{project['id']}/rewrite",
        json={"jd_id": job["jd_id"], "resume_version_id": "missing_resume_version"},
    )
    missing_match = client.post(
        f"/api/projects/{project['id']}/rewrite",
        json={"jd_id": job["jd_id"], "match_report_id": "missing_match"},
    )
    missing_profile = client.post(
        f"/api/projects/{project['id']}/rewrite",
        json={"jd_id": job["jd_id"], "profile_id": "missing_profile"},
    )

    assert missing_resume.status_code == 404
    assert get_error(missing_resume)["code"] == "resume_version_not_found"
    assert missing_match.status_code == 404
    assert get_error(missing_match)["code"] == "match_report_not_found"
    assert missing_profile.status_code == 404
    assert get_error(missing_profile)["code"] == "profile_not_found"


def test_project_rewrite_rejects_insufficient_project_facts():
    client = make_client()
    project = _create_project(
        client,
        background=None,
        tech_stack=[],
        responsibilities=[],
        results=[],
        evidence=[],
    )
    job = _create_job(client)

    response = client.post(
        f"/api/projects/{project['id']}/rewrite",
        json={"jd_id": job["jd_id"]},
    )

    assert response.status_code == 400
    assert get_error(response)["code"] == "project_facts_insufficient"


def test_project_rewrite_accepts_optional_refs_and_does_not_return_resume_raw_text():
    client = make_client()
    resume_version_id = _create_resume_version(client)
    profile = _create_profile(client)
    project = _create_project(
        client,
        profile_id=profile["id"],
        resume_version_id=resume_version_id,
    )
    job = _create_job(client)
    match_report = _create_match_report(client, resume_version_id, job["jd_id"])

    response = client.post(
        f"/api/projects/{project['id']}/rewrite",
        json={
            "jd_id": job["jd_id"],
            "resume_version_id": resume_version_id,
            "match_report_id": match_report["match_report_id"],
            "profile_id": profile["id"],
        },
    )

    assert response.status_code == 201
    data = get_data(response)
    assert data["resume_version_id"] == resume_version_id
    assert data["match_report_id"] == match_report["match_report_id"]
    assert data["profile_id"] == profile["id"]
    assert "PRIVATE_RESUME_TEXT" not in response.text
    _assert_private_safe(data)
