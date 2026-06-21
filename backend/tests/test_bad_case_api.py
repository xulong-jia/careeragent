from conftest import get_data, get_error, make_client


PRIVATE_TEXT_KEYS = {
    "raw_text",
    "jd_raw_text",
    "chunk_text",
    "full_text",
    "resume_text",
    "job_text",
}


def _payload(**overrides):
    payload = {
        "source_type": "match_report",
        "source_id": "match_0001",
        "category": "match_score_inaccurate",
        "title": "Synthetic score issue",
        "description": "Synthetic summary of a match score issue.",
        "expected_behavior": "Expected score to reflect missing required skills.",
        "actual_behavior": "Actual score stayed high.",
        "suggested_fix": "Adjust deterministic scoring weights.",
    }
    payload.update(overrides)
    return payload


def _create_bad_case(client, **overrides):
    response = client.post("/api/evaluations/bad-cases", json=_payload(**overrides))
    assert response.status_code == 201
    return get_data(response)


def _assert_private_safe(value):
    if isinstance(value, dict):
        assert PRIVATE_TEXT_KEYS.isdisjoint(value.keys())
        for child in value.values():
            _assert_private_safe(child)
    elif isinstance(value, list):
        for child in value:
            _assert_private_safe(child)


def test_create_bad_case_success_with_defaults_and_safe_response():
    client = make_client()

    data = _create_bad_case(client)

    assert data["id"].startswith("bad_case_")
    assert data["user_id"] == "default"
    assert data["source_type"] == "match_report"
    assert data["source_id"] == "match_0001"
    assert data["category"] == "match_score_inaccurate"
    assert data["severity"] == "medium"
    assert data["status"] == "open"
    assert data["resolved_at"] is None
    _assert_private_safe(data)


def test_list_bad_cases_and_filters():
    client = make_client()
    first = _create_bad_case(
        client,
        source_type="match_report",
        source_id="match_0001",
        category="match_score_inaccurate",
        severity="high",
        title="First synthetic case",
    )
    second = _create_bad_case(
        client,
        source_type="agent_run",
        source_id="agent_run_0001",
        category="agent_step_failed",
        severity="critical",
        title="Second synthetic case",
    )

    list_response = client.get("/api/evaluations/bad-cases")
    assert list_response.status_code == 200
    listed = get_data(list_response)
    assert listed["total"] == 2
    assert [item["id"] for item in listed["items"]] == [second["id"], first["id"]]

    filter_cases = [
        ("source_type", "agent_run", second["id"]),
        ("source_id", "match_0001", first["id"]),
        ("category", "agent_step_failed", second["id"]),
        ("severity", "high", first["id"]),
        ("status", "open", second["id"]),
    ]
    for field, value, expected_id in filter_cases:
        response = client.get("/api/evaluations/bad-cases", params={field: value})
        assert response.status_code == 200
        data = get_data(response)
        assert data["total"] >= 1
        assert data["items"][0]["id"] == expected_id


def test_get_bad_case_detail():
    client = make_client()
    created = _create_bad_case(client)

    response = client.get(f"/api/evaluations/bad-cases/{created['id']}")

    assert response.status_code == 200
    detail = get_data(response)
    assert detail["id"] == created["id"]
    assert detail["description"] == "Synthetic summary of a match score issue."
    _assert_private_safe(detail)


def test_patch_bad_case_status_and_resolution_fields():
    client = make_client()
    created = _create_bad_case(client)

    reviewing_response = client.patch(
        f"/api/evaluations/bad-cases/{created['id']}",
        json={"status": "reviewing"},
    )
    assert reviewing_response.status_code == 200
    reviewing = get_data(reviewing_response)
    assert reviewing["status"] == "reviewing"
    assert reviewing["resolved_at"] is None

    fixed_response = client.patch(
        f"/api/evaluations/bad-cases/{created['id']}",
        json={
            "status": "fixed",
            "severity": "low",
            "suggested_fix": "Synthetic fix summary.",
        },
    )
    assert fixed_response.status_code == 200
    fixed = get_data(fixed_response)
    assert fixed["status"] == "fixed"
    assert fixed["severity"] == "low"
    assert fixed["suggested_fix"] == "Synthetic fix summary."
    assert fixed["resolved_at"] is not None

    reopened_response = client.patch(
        f"/api/evaluations/bad-cases/{created['id']}",
        json={"status": "open"},
    )
    assert reopened_response.status_code == 200
    reopened = get_data(reopened_response)
    assert reopened["status"] == "open"
    assert reopened["resolved_at"] is None


def test_patch_bad_case_text_and_category_fields():
    client = make_client()
    created = _create_bad_case(client)

    response = client.patch(
        f"/api/evaluations/bad-cases/{created['id']}",
        json={
            "category": "privacy_risk",
            "title": "Updated synthetic title",
            "description": "Updated synthetic summary.",
            "expected_behavior": "Expected private text to stay hidden.",
            "actual_behavior": "Actual response included too much detail.",
        },
    )

    assert response.status_code == 200
    data = get_data(response)
    assert data["category"] == "privacy_risk"
    assert data["title"] == "Updated synthetic title"
    assert data["description"] == "Updated synthetic summary."
    assert data["expected_behavior"] == "Expected private text to stay hidden."
    assert data["actual_behavior"] == "Actual response included too much detail."


def test_missing_bad_case_returns_unified_error():
    client = make_client()

    detail = client.get("/api/evaluations/bad-cases/missing_bad_case")
    patch = client.patch(
        "/api/evaluations/bad-cases/missing_bad_case",
        json={"status": "reviewing"},
    )

    assert detail.status_code == 404
    assert get_error(detail)["code"] == "bad_case_not_found"
    assert patch.status_code == 404
    assert get_error(patch)["code"] == "bad_case_not_found"


def test_bad_case_create_rejects_invalid_allowed_values():
    client = make_client()

    invalid_cases = [
        ("source_type", "unknown_source"),
        ("category", "unknown_category"),
        ("severity", "urgent"),
    ]
    for field, value in invalid_cases:
        response = client.post(
            "/api/evaluations/bad-cases",
            json=_payload(**{field: value}),
        )
        assert response.status_code == 400
        error = get_error(response)
        assert error["code"] == "bad_case_invalid_field"
        assert error["details"]["field"] == field


def test_bad_case_patch_rejects_invalid_allowed_values():
    client = make_client()
    created = _create_bad_case(client)

    invalid_cases = [
        ("category", "unknown_category"),
        ("severity", "urgent"),
        ("status", "closed"),
    ]
    for field, value in invalid_cases:
        response = client.patch(
            f"/api/evaluations/bad-cases/{created['id']}",
            json={field: value},
        )
        assert response.status_code == 400
        error = get_error(response)
        assert error["code"] == "bad_case_invalid_field"
        assert error["details"]["field"] == field


def test_bad_case_rejects_empty_title_and_description():
    client = make_client()

    empty_title = client.post(
        "/api/evaluations/bad-cases",
        json=_payload(title="   "),
    )
    empty_description = client.post(
        "/api/evaluations/bad-cases",
        json=_payload(description="   "),
    )

    assert empty_title.status_code == 400
    assert get_error(empty_title)["code"] == "bad_case_invalid_field"
    assert empty_description.status_code == 400
    assert get_error(empty_description)["code"] == "bad_case_invalid_field"


def test_bad_case_extra_sensitive_fields_are_rejected():
    client = make_client()
    payload = _payload(raw_text="Synthetic raw private text should not be accepted.")

    response = client.post("/api/evaluations/bad-cases", json=payload)

    assert response.status_code == 422
    error = get_error(response)
    assert error["code"] == "validation_error"
