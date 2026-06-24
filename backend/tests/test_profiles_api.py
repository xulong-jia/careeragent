import re

from conftest import get_data, get_error, make_client


PROFILE_ID_PATTERN = re.compile(r"^profile_[0-9a-f]{12}$")
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


def _profile_payload(**overrides):
    payload = {
        "target_roles": ["LLM Application Engineer", "Python Backend Developer"],
        "target_industries": ["Internet", "Enterprise Software"],
        "target_locations": ["Shanghai", "Sydney"],
        "skill_map": {
            "programming": ["Python", "TypeScript"],
            "backend": ["FastAPI"],
            "ai": ["RAG"],
        },
        "preferences": {
            "preferred_company_type": ["Product"],
            "language": ["English", "Chinese"],
        },
        "source_resume_version_id": None,
    }
    payload.update(overrides)
    return payload


def _create_profile(client, **overrides):
    response = client.post("/api/profiles", json=_profile_payload(**overrides))
    assert response.status_code == 201
    return get_data(response)


def _create_resume_version(client, content: bytes = b"PRIVATE_RESUME_TEXT Python"):
    response = client.post(
        "/api/resumes/upload",
        files={"file": ("profile-source.md", content, "text/markdown")},
    )
    assert response.status_code == 201
    resume_id = get_data(response)["resume_id"]
    versions_response = client.get(f"/api/resumes/{resume_id}/versions")
    assert versions_response.status_code == 200
    return get_data(versions_response)["items"][0]["resume_version_id"]


def test_create_profile_success():
    client = make_client()

    data = _create_profile(client)

    assert PROFILE_ID_PATTERN.match(data["id"])
    assert data["user_id"] == "default"
    assert data["target_roles"] == [
        "LLM Application Engineer",
        "Python Backend Developer",
    ]
    assert data["target_locations"] == ["Shanghai", "Sydney"]
    assert data["skill_map"]["backend"] == ["FastAPI"]
    assert data["source_resume_version_id"] is None
    assert data["created_at"]
    assert data["updated_at"]
    _assert_private_safe(data)


def test_list_profiles_and_get_detail():
    client = make_client()
    first = _create_profile(client, target_roles=["Backend Engineer"])
    second = _create_profile(client, target_roles=["AI Engineer"])

    list_response = client.get("/api/profiles")
    detail_response = client.get(f"/api/profiles/{first['id']}")

    assert list_response.status_code == 200
    listed = get_data(list_response)
    assert listed["total"] == 2
    assert {item["id"] for item in listed["items"]} == {first["id"], second["id"]}
    assert detail_response.status_code == 200
    assert get_data(detail_response)["id"] == first["id"]


def test_patch_profile_updates_fields_and_can_clear_source_version():
    client = make_client()
    source_version_id = _create_resume_version(client)
    created = _create_profile(client, source_resume_version_id=source_version_id)

    response = client.patch(
        f"/api/profiles/{created['id']}",
        json={
            "target_roles": ["Platform Engineer"],
            "target_locations": ["Beijing"],
            "skill_map": {"backend": ["FastAPI", "SQLAlchemy"]},
            "source_resume_version_id": None,
        },
    )

    assert response.status_code == 200
    data = get_data(response)
    assert data["target_roles"] == ["Platform Engineer"]
    assert data["target_locations"] == ["Beijing"]
    assert data["skill_map"]["backend"] == ["FastAPI", "SQLAlchemy"]
    assert data["source_resume_version_id"] is None


def test_profile_summary_completeness_ready_and_incomplete():
    client = make_client()
    ready_profile = _create_profile(client)
    incomplete_profile = _create_profile(
        client,
        target_roles=[],
        target_locations=[],
        skill_map={},
    )

    ready_response = client.get(f"/api/profiles/{ready_profile['id']}/summary")
    incomplete_response = client.get(
        f"/api/profiles/{incomplete_profile['id']}/summary"
    )

    assert ready_response.status_code == 200
    ready = get_data(ready_response)
    assert ready["completeness_score"] == 100
    assert ready["readiness_level"] == "ready"
    assert ready["missing_fields"] == []
    assert ready["target_roles_count"] == 2
    assert ready["target_locations_count"] == 2
    assert ready["skill_categories_count"] == 3

    assert incomplete_response.status_code == 200
    incomplete = get_data(incomplete_response)
    assert incomplete["completeness_score"] == 0
    assert incomplete["readiness_level"] == "incomplete"
    assert set(incomplete["missing_fields"]) == {
        "target_roles",
        "target_locations",
        "skill_map",
    }


def test_create_profile_with_existing_source_resume_version():
    client = make_client()
    source_version_id = _create_resume_version(client)

    data = _create_profile(client, source_resume_version_id=source_version_id)

    assert data["source_resume_version_id"] == source_version_id


def test_create_profile_rejects_missing_source_resume_version():
    client = make_client()

    response = client.post(
        "/api/profiles",
        json=_profile_payload(source_resume_version_id="missing_version"),
    )

    assert response.status_code == 404
    assert get_error(response)["code"] == "resume_version_not_found"


def test_profile_responses_do_not_return_resume_raw_text():
    client = make_client()
    source_version_id = _create_resume_version(client)
    created = _create_profile(client, source_resume_version_id=source_version_id)

    detail_response = client.get(f"/api/profiles/{created['id']}")
    list_response = client.get("/api/profiles")
    summary_response = client.get(f"/api/profiles/{created['id']}/summary")

    assert detail_response.status_code == 200
    assert list_response.status_code == 200
    assert summary_response.status_code == 200
    for response in (detail_response, list_response, summary_response):
        payload_text = response.text
        assert "PRIVATE_RESUME_TEXT" not in payload_text
        _assert_private_safe(get_data(response))


def test_profile_invalid_payload_returns_validation_error():
    client = make_client()

    invalid_type = client.post(
        "/api/profiles",
        json=_profile_payload(target_roles="Backend Engineer"),
    )
    empty_item = client.post(
        "/api/profiles",
        json=_profile_payload(target_roles=["Backend Engineer", ""]),
    )
    invalid_patch = client.patch(
        "/api/profiles/missing_profile",
        json={"skill_map": "not a dict"},
    )

    assert invalid_type.status_code == 422
    assert get_error(invalid_type)["code"] == "validation_error"
    assert empty_item.status_code == 400
    assert get_error(empty_item)["code"] == "validation_error"
    assert invalid_patch.status_code == 422
    assert get_error(invalid_patch)["code"] == "validation_error"


def test_profile_missing_profile_returns_404():
    client = make_client()

    detail = client.get("/api/profiles/missing_profile")
    patch = client.patch(
        "/api/profiles/missing_profile",
        json={"target_roles": ["Backend Engineer"]},
    )
    summary = client.get("/api/profiles/missing_profile/summary")

    assert detail.status_code == 404
    assert patch.status_code == 404
    assert summary.status_code == 404
    assert get_error(detail)["code"] == "profile_not_found"
    assert get_error(patch)["code"] == "profile_not_found"
    assert get_error(summary)["code"] == "profile_not_found"
