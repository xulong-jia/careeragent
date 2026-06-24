import re

from conftest import get_data, get_error, make_client


PROJECT_ID_PATTERN = re.compile(r"^project_[0-9a-f]{12}$")
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


def _project_payload(**overrides):
    payload = {
        "profile_id": None,
        "resume_version_id": None,
        "name": "CareerAgent RAG Workbench",
        "role": "Backend Engineer",
        "period": "2026-02 to 2026-05",
        "background": "Built a local deterministic RAG workflow for job preparation.",
        "tech_stack": ["Python", "FastAPI", "SQLite"],
        "responsibilities": [
            "Designed FastAPI routes for document indexing.",
            "Implemented lexical retrieval with source snippets.",
        ],
        "results": [
            "Created reproducible synthetic smoke tests for retrieval behavior.",
        ],
        "evidence": [
            {
                "type": "repository",
                "description": "Synthetic test suite and API docs.",
                "source": "local_repo",
            }
        ],
        "status": "active",
    }
    payload.update(overrides)
    return payload


def _create_project(client, **overrides):
    response = client.post("/api/projects", json=_project_payload(**overrides))
    assert response.status_code == 201
    return get_data(response)


def _create_profile(client):
    response = client.post(
        "/api/profiles",
        json={
            "target_roles": ["Backend Engineer"],
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
        files={"file": ("project-source.md", content, "text/markdown")},
    )
    assert response.status_code == 201
    resume_id = get_data(response)["resume_id"]
    versions_response = client.get(f"/api/resumes/{resume_id}/versions")
    assert versions_response.status_code == 200
    return get_data(versions_response)["items"][0]["resume_version_id"]


def test_create_project_success():
    client = make_client()

    data = _create_project(client)

    assert PROJECT_ID_PATTERN.match(data["id"])
    assert data["user_id"] == "default"
    assert data["name"] == "CareerAgent RAG Workbench"
    assert data["role"] == "Backend Engineer"
    assert data["tech_stack"] == ["Python", "FastAPI", "SQLite"]
    assert data["responsibilities"][0].startswith("Designed FastAPI")
    assert data["results"][0].startswith("Created reproducible")
    assert data["evidence"][0]["type"] == "repository"
    assert data["status"] == "active"
    assert data["created_at"]
    assert data["updated_at"]
    _assert_private_safe(data)


def test_create_project_defaults_array_fields_to_empty_lists():
    client = make_client()

    data = _create_project(
        client,
        tech_stack=[],
        responsibilities=[],
        results=[],
        evidence=[],
    )

    assert data["tech_stack"] == []
    assert data["responsibilities"] == []
    assert data["results"] == []
    assert data["evidence"] == []


def test_create_project_rejects_blank_name():
    client = make_client()

    response = client.post("/api/projects", json=_project_payload(name="   "))

    assert response.status_code == 400
    assert get_error(response)["code"] == "validation_error"


def test_list_projects_and_get_detail():
    client = make_client()
    first = _create_project(client, name="First Project")
    second = _create_project(client, name="Second Project")

    list_response = client.get("/api/projects")
    detail_response = client.get(f"/api/projects/{first['id']}")

    assert list_response.status_code == 200
    listed = get_data(list_response)
    assert listed["total"] == 2
    assert {item["id"] for item in listed["items"]} == {first["id"], second["id"]}
    assert detail_response.status_code == 200
    assert get_data(detail_response)["id"] == first["id"]


def test_patch_project_updates_fields():
    client = make_client()
    created = _create_project(client)

    response = client.patch(
        f"/api/projects/{created['id']}",
        json={
            "name": "Updated Project",
            "role": "Platform Engineer",
            "tech_stack": ["Python", "SQLAlchemy"],
            "status": "archived",
        },
    )

    assert response.status_code == 200
    data = get_data(response)
    assert data["name"] == "Updated Project"
    assert data["role"] == "Platform Engineer"
    assert data["tech_stack"] == ["Python", "SQLAlchemy"]
    assert data["status"] == "archived"


def test_project_status_is_limited_to_active_or_archived():
    client = make_client()
    created = _create_project(client)

    create_response = client.post(
        "/api/projects", json=_project_payload(status="deleted")
    )
    patch_response = client.patch(
        f"/api/projects/{created['id']}", json={"status": "deleted"}
    )

    assert create_response.status_code == 422
    assert get_error(create_response)["code"] == "validation_error"
    assert patch_response.status_code == 422
    assert get_error(patch_response)["code"] == "validation_error"


def test_list_projects_filters_by_status_profile_and_resume_version():
    client = make_client()
    profile = _create_profile(client)
    resume_version_id = _create_resume_version(client)
    matching = _create_project(
        client,
        profile_id=profile["id"],
        resume_version_id=resume_version_id,
        status="active",
    )
    _create_project(client, status="archived")

    by_status = client.get("/api/projects", params={"status": "active"})
    by_profile = client.get("/api/projects", params={"profile_id": profile["id"]})
    by_resume = client.get(
        "/api/projects", params={"resume_version_id": resume_version_id}
    )

    assert by_status.status_code == 200
    assert [item["id"] for item in get_data(by_status)["items"]] == [matching["id"]]
    assert by_profile.status_code == 200
    assert [item["id"] for item in get_data(by_profile)["items"]] == [matching["id"]]
    assert by_resume.status_code == 200
    assert [item["id"] for item in get_data(by_resume)["items"]] == [matching["id"]]


def test_create_project_with_existing_profile_and_resume_version():
    client = make_client()
    profile = _create_profile(client)
    resume_version_id = _create_resume_version(client)

    data = _create_project(
        client,
        profile_id=profile["id"],
        resume_version_id=resume_version_id,
    )

    assert data["profile_id"] == profile["id"]
    assert data["resume_version_id"] == resume_version_id


def test_create_project_rejects_missing_profile_or_resume_version():
    client = make_client()

    missing_profile = client.post(
        "/api/projects", json=_project_payload(profile_id="missing_profile")
    )
    missing_resume_version = client.post(
        "/api/projects",
        json=_project_payload(resume_version_id="missing_resume_version"),
    )

    assert missing_profile.status_code == 404
    assert get_error(missing_profile)["code"] == "profile_not_found"
    assert missing_resume_version.status_code == 404
    assert get_error(missing_resume_version)["code"] == "resume_version_not_found"


def test_project_responses_do_not_return_resume_raw_text():
    client = make_client()
    resume_version_id = _create_resume_version(client)
    created = _create_project(client, resume_version_id=resume_version_id)

    detail_response = client.get(f"/api/projects/{created['id']}")
    list_response = client.get("/api/projects")

    assert detail_response.status_code == 200
    assert list_response.status_code == 200
    for response in (detail_response, list_response):
        assert "PRIVATE_RESUME_TEXT" not in response.text
        _assert_private_safe(get_data(response))


def test_project_invalid_payload_returns_validation_error():
    client = make_client()

    string_list_field = client.post(
        "/api/projects", json=_project_payload(tech_stack="FastAPI")
    )
    empty_patch = client.patch("/api/projects/missing_project", json={})

    assert string_list_field.status_code == 422
    assert get_error(string_list_field)["code"] == "validation_error"
    assert empty_patch.status_code == 400
    assert get_error(empty_patch)["code"] == "validation_error"


def test_project_missing_project_returns_404():
    client = make_client()

    detail = client.get("/api/projects/missing_project")
    patch = client.patch("/api/projects/missing_project", json={"name": "Updated"})

    assert detail.status_code == 404
    assert patch.status_code == 404
    assert get_error(detail)["code"] == "project_not_found"
    assert get_error(patch)["code"] == "project_not_found"
