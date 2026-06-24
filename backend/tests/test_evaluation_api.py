import re

from conftest import get_data, get_error, make_client


EVAL_RUN_ID_PATTERN = re.compile(r"^eval_run_[0-9a-f]{12}$")
EVAL_CASE_ID_PATTERN = re.compile(r"^eval_case_[0-9a-f]{12}$")
EVAL_RESULT_ID_PATTERN = re.compile(r"^eval_result_[0-9a-f]{12}$")
PRIVATE_TEXT_KEYS = {
    "raw_text",
    "jd_raw_text",
    "chunk_text",
    "full_text",
    "resume_text",
    "job_text",
}


def _assert_private_safe(value):
    if isinstance(value, dict):
        assert PRIVATE_TEXT_KEYS.isdisjoint(value.keys())
        for child in value.values():
            _assert_private_safe(child)
    elif isinstance(value, list):
        for child in value:
            _assert_private_safe(child)


def _bad_case_payload(**overrides):
    payload = {
        "source_type": "match_report",
        "source_id": "match_0001",
        "category": "match_score_inaccurate",
        "severity": "high",
        "title": "Synthetic score issue",
        "description": "Synthetic summary of score mismatch.",
        "expected_behavior": "Expected lower score for missing requirements.",
        "actual_behavior": "Actual score stayed high.",
        "suggested_fix": "Adjust deterministic scoring rules.",
    }
    payload.update(overrides)
    return payload


def _create_bad_case(client, **overrides):
    response = client.post(
        "/api/evaluations/bad-cases",
        json=_bad_case_payload(**overrides),
    )
    assert response.status_code == 201
    return get_data(response)


def _manual_case_payload(**overrides):
    payload = {
        "module": "match",
        "dataset_name": "manual_regression",
        "case_name": "Manual match schema case",
        "input_payload": {"match_report_id": "match_0001"},
        "expected_output": {"required_fields": ["total_score"]},
        "tags": ["manual", "regression"],
        "source_type": "manual",
    }
    payload.update(overrides)
    return payload


def test_create_manual_evaluation_case():
    client = make_client()

    response = client.post("/api/evaluations/cases", json=_manual_case_payload())

    assert response.status_code == 201
    data = get_data(response)
    assert EVAL_CASE_ID_PATTERN.match(data["id"])
    assert data["module"] == "match"
    assert data["dataset_name"] == "manual_regression"
    assert data["source_type"] == "manual"
    assert data["bad_case_id"] is None
    assert data["tags"] == ["manual", "regression"]
    _assert_private_safe(data)


def test_create_evaluation_case_from_bad_case_keeps_summary_refs_only():
    client = make_client()
    bad_case = _create_bad_case(client)

    response = client.post(
        f"/api/evaluations/cases/from-bad-case/{bad_case['id']}",
    )

    assert response.status_code == 201
    data = get_data(response)
    assert EVAL_CASE_ID_PATTERN.match(data["id"])
    assert data["source_type"] == "bad_case"
    assert data["bad_case_id"] == bad_case["id"]
    assert data["module"] == "match"
    assert data["input_payload"]["source_id"] == "match_0001"
    assert data["input_payload"]["description_summary"]
    assert "raw_text" not in data["input_payload"]
    _assert_private_safe(data)


def test_run_synthetic_smoke_evaluation_creates_run_cases_and_results():
    client = make_client()

    response = client.post(
        "/api/evaluations/runs",
        json={"name": "Synthetic smoke evaluation"},
    )

    assert response.status_code == 201
    summary = get_data(response)
    run = summary["run"]
    assert EVAL_RUN_ID_PATTERN.match(run["id"])
    assert run["name"] == "Synthetic smoke evaluation"
    assert run["module"] == "all"
    assert run["dataset_name"] == "synthetic_smoke_v1"
    assert run["status"] == "completed"
    assert summary["results_count"] == 5
    assert run["metrics"]["total_count"] == 5
    assert run["metrics"]["passed_count"] == 5
    assert run["metrics"]["failed_count"] == 0
    assert run["metrics"]["pass_rate"] == 1.0
    assert set(run["metrics"]["by_module"]) == {
        "match",
        "rag",
        "agent",
        "application",
        "bad_case",
    }
    _assert_private_safe(summary)

    results_response = client.get(f"/api/evaluations/runs/{run['id']}/results")
    assert results_response.status_code == 200
    results = get_data(results_response)
    assert results["total"] == 5
    assert all(EVAL_RESULT_ID_PATTERN.match(item["id"]) for item in results["items"])
    assert all(item["passed"] is True for item in results["items"])
    _assert_private_safe(results)


def test_list_run_detail_results_cases_and_stats():
    client = make_client()
    run = get_data(
        client.post("/api/evaluations/runs", json={"module": "rag"})
    )["run"]

    runs_response = client.get("/api/evaluations/runs")
    detail_response = client.get(f"/api/evaluations/runs/{run['id']}")
    results_response = client.get(f"/api/evaluations/runs/{run['id']}/results")
    cases_response = client.get(
        "/api/evaluations/cases",
        params={"module": "rag", "dataset_name": "synthetic_smoke_v1"},
    )
    stats_response = client.get("/api/evaluations/stats")

    assert runs_response.status_code == 200
    assert get_data(runs_response)["items"][0]["id"] == run["id"]
    assert detail_response.status_code == 200
    assert get_data(detail_response)["run"]["id"] == run["id"]
    assert results_response.status_code == 200
    assert get_data(results_response)["total"] == 1
    assert cases_response.status_code == 200
    cases = get_data(cases_response)
    assert cases["total"] == 1
    assert cases["items"][0]["module"] == "rag"
    assert stats_response.status_code == 200
    stats = get_data(stats_response)
    assert stats["total_runs"] == 1
    assert stats["latest_run_status"] == "completed"
    assert stats["latest_pass_rate"] == 1.0
    assert stats["total_cases"] >= 1
    assert stats["failed_results"] == 0
    assert stats["by_module"]["rag"] >= 1


def test_invalid_evaluation_module_returns_unified_error():
    client = make_client()

    run_response = client.post(
        "/api/evaluations/runs",
        json={"module": "unknown"},
    )
    case_response = client.post(
        "/api/evaluations/cases",
        json=_manual_case_payload(module="unknown"),
    )

    assert run_response.status_code == 400
    assert get_error(run_response)["code"] == "evaluation_invalid_field"
    assert case_response.status_code == 400
    assert get_error(case_response)["code"] == "evaluation_invalid_field"


def test_evaluation_case_rejects_private_raw_text_payloads():
    client = make_client()

    response = client.post(
        "/api/evaluations/cases",
        json=_manual_case_payload(input_payload={"raw_text": "private resume text"}),
    )

    assert response.status_code == 400
    error = get_error(response)
    assert error["code"] == "evaluation_private_text_rejected"


def test_bad_case_api_still_works_after_evaluation_routes_added():
    client = make_client()

    created = _create_bad_case(client)
    list_response = client.get("/api/evaluations/bad-cases")
    detail_response = client.get(f"/api/evaluations/bad-cases/{created['id']}")
    patch_response = client.patch(
        f"/api/evaluations/bad-cases/{created['id']}",
        json={"status": "reviewing"},
    )

    assert list_response.status_code == 200
    assert get_data(list_response)["total"] == 1
    assert detail_response.status_code == 200
    assert get_data(detail_response)["id"] == created["id"]
    assert patch_response.status_code == 200
    assert get_data(patch_response)["status"] == "reviewing"
