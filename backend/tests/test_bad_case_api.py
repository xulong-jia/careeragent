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
        "root_cause": "Synthetic root cause summary.",
        "fix_strategy": "Synthetic fix strategy summary.",
        "tags": ["regression", "match"],
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
    assert data["root_cause"] == "Synthetic root cause summary."
    assert data["fix_strategy"] == "Synthetic fix strategy summary."
    assert data["tags"] == ["regression", "match"]
    assert data["added_to_eval_set"] is False
    assert data["verified_at"] is None
    assert data["regression_evaluation_case_id"] is None
    assert data["regression_evaluation_run_id"] is None
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

    verified_response = client.patch(
        f"/api/evaluations/bad-cases/{created['id']}",
        json={"status": "verified"},
    )
    assert verified_response.status_code == 200
    verified = get_data(verified_response)
    assert verified["status"] == "verified"
    assert verified["resolved_at"] is not None
    assert verified["verified_at"] is not None

    reopened_response = client.patch(
        f"/api/evaluations/bad-cases/{created['id']}",
        json={"status": "open"},
    )
    assert reopened_response.status_code == 200
    reopened = get_data(reopened_response)
    assert reopened["status"] == "open"
    assert reopened["resolved_at"] is None
    assert reopened["verified_at"] is None


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
            "root_cause": "Summary-only root cause.",
            "fix_strategy": "Summary-only fix strategy.",
            "tags": ["privacy", "regression"],
        },
    )

    assert response.status_code == 200
    data = get_data(response)
    assert data["category"] == "privacy_risk"
    assert data["title"] == "Updated synthetic title"
    assert data["description"] == "Updated synthetic summary."
    assert data["expected_behavior"] == "Expected private text to stay hidden."
    assert data["actual_behavior"] == "Actual response included too much detail."
    assert data["root_cause"] == "Summary-only root cause."
    assert data["fix_strategy"] == "Summary-only fix strategy."
    assert data["tags"] == ["privacy", "regression"]


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


def test_direct_bad_case_route_and_stats():
    client = make_client()
    created = get_data(client.post("/api/bad-cases", json=_payload()))

    stats_response = client.get("/api/bad-cases/stats")
    list_response = client.get("/api/bad-cases")
    detail_response = client.get(f"/api/bad-cases/{created['id']}")

    assert stats_response.status_code == 200
    stats = get_data(stats_response)
    assert stats["total"] == 1
    assert stats["open_count"] == 1
    assert stats["added_to_eval_set_count"] == 0
    assert stats["verified_count"] == 0
    assert stats["by_status"]["open"] == 1
    assert stats["by_module"]["match"] == 1
    assert stats["by_case_type"]["match_score_inaccurate"] == 1
    assert list_response.status_code == 200
    assert get_data(list_response)["items"][0]["id"] == created["id"]
    assert detail_response.status_code == 200
    assert get_data(detail_response)["id"] == created["id"]


def test_add_bad_case_to_eval_is_idempotent_and_privacy_safe():
    client = make_client()
    created = _create_bad_case(client)

    first_response = client.post(f"/api/bad-cases/{created['id']}/add-to-eval")
    second_response = client.post(f"/api/bad-cases/{created['id']}/add-to-eval")

    assert first_response.status_code == 201
    first = get_data(first_response)
    assert first["created"] is True
    assert first["bad_case"]["added_to_eval_set"] is True
    assert first["bad_case"]["regression_evaluation_case_id"] == first["evaluation_case"]["id"]
    assert first["evaluation_case"]["dataset_name"] == "regression"
    assert first["evaluation_case"]["source_type"] == "bad_case"
    assert first["evaluation_case"]["bad_case_id"] == created["id"]
    _assert_private_safe(first)

    assert second_response.status_code == 201
    second = get_data(second_response)
    assert second["created"] is False
    assert second["evaluation_case"]["id"] == first["evaluation_case"]["id"]
