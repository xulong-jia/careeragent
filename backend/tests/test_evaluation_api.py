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
    assert data["dataset_name"] == "synthetic_smoke_v1"
    assert "raw_text" not in data["input_payload"]
    _assert_private_safe(data)


def test_list_evaluation_datasets_includes_synthetic_and_file_smoke_sets():
    client = make_client()

    response = client.get("/api/evaluations/datasets")

    assert response.status_code == 200
    data = get_data(response)
    dataset_keys = {
        (item["dataset_name"], item["module"], item["source_type"])
        for item in data["items"]
    }
    assert ("synthetic_smoke_v1", "jd_parser", "built-in") in dataset_keys
    assert ("synthetic_smoke_v1", "resume_parser", "built-in") in dataset_keys
    assert ("smoke", "rag", "file") in dataset_keys


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
    assert summary["results_count"] == 7
    assert run["metrics"]["total_count"] == 7
    assert run["metrics"]["passed_count"] == 7
    assert run["metrics"]["failed_count"] == 0
    assert run["metrics"]["failed_case_ids"] == []
    assert run["metrics"]["pass_rate"] == 1.0
    assert set(run["metrics"]["by_module"]) == {
        "jd_parser",
        "resume_parser",
        "match",
        "rag",
        "agent",
        "application",
        "bad_case",
    }
    assert run["run_config"]["prompt_version"] == "parser-foundation-v2.3"
    assert run["run_config"]["schema_version"] == "v2.3"
    assert run["run_config"]["retrieval_version"] == "local-vector-v1"
    assert run["run_config"]["model_version"] == "none"
    assert run["run_config"]["evaluation_version"] == "v2.3"
    assert run["run_config"]["code_version"]
    _assert_private_safe(summary)

    results_response = client.get(f"/api/evaluations/runs/{run['id']}/results")
    assert results_response.status_code == 200
    results = get_data(results_response)
    assert results["total"] == 7
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


def test_bad_case_regression_pass_marks_case_verified():
    client = make_client()
    bad_case = _create_bad_case(client)
    link = get_data(client.post(f"/api/bad-cases/{bad_case['id']}/add-to-eval"))

    response = client.post(
        "/api/evaluations/runs",
        json={"module": "match", "dataset_name": "regression"},
    )

    assert response.status_code == 201
    run = get_data(response)["run"]
    assert run["metrics"]["failed_count"] == 0
    detail = get_data(client.get(f"/api/bad-cases/{bad_case['id']}"))
    assert detail["status"] == "verified"
    assert detail["verified_at"] is not None
    assert detail["resolved_at"] is not None
    assert detail["regression_evaluation_run_id"] == run["id"]
    assert detail["regression_evaluation_case_id"] == link["evaluation_case"]["id"]


def test_bad_case_regression_failure_keeps_case_unverified_and_records_failed_case():
    client = make_client()
    bad_case = _create_bad_case(client)
    manual_case = get_data(
        client.post(
            "/api/evaluations/cases",
            json=_manual_case_payload(
                dataset_name="regression_failure",
                case_name="Failing bad case regression",
                input_payload={"resume_signals": [], "jd_requirements": []},
                expected_output={
                    "required_fields": ["total_score", "missing_required_field"],
                },
                source_type="bad_case",
                bad_case_id=bad_case["id"],
            ),
        )
    )

    response = client.post(
        "/api/evaluations/runs",
        json={"module": "match", "dataset_name": "regression_failure"},
    )

    assert response.status_code == 201
    run = get_data(response)["run"]
    assert manual_case["id"] in run["metrics"]["failed_case_ids"]
    detail = get_data(client.get(f"/api/bad-cases/{bad_case['id']}"))
    assert detail["status"] != "verified"
    assert detail["verified_at"] is None
    assert detail["regression_evaluation_run_id"] == run["id"]
    assert detail["regression_evaluation_case_id"] == manual_case["id"]


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
