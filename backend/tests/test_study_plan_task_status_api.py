from conftest import get_data, get_error, make_client
from app.models.study_plan import StudyPlan
from test_study_plan_generate_api import (
    _assert_private_safe,
    _create_match_report,
    _create_profile,
)


def _generate_plan(client, **payload):
    request_payload = {"target_role": "Backend AI Engineer"}
    request_payload.update(payload)
    response = client.post("/api/study-plans/generate", json=request_payload)
    assert response.status_code == 201
    return get_data(response)


def _first_two_task_ids(plan):
    task_ids = [
        task["task_id"]
        for phase in plan["phases"]
        for task in phase["tasks"]
    ]
    assert len(task_ids) >= 2
    return task_ids[0], task_ids[1]


def test_list_study_plans_empty():
    client = make_client()

    response = client.get("/api/study-plans")

    assert response.status_code == 200
    data = get_data(response)
    assert data == {"items": [], "total": 0}


def test_list_study_plans_after_generated_plans_and_filters(db_session):
    client = make_client()
    profile = _create_profile(client)
    match_report = _create_match_report(client)
    first = _generate_plan(
        client,
        target_role="Backend AI Engineer",
        profile_id=profile["id"],
    )
    second = _generate_plan(
        client,
        target_role="Data Engineer",
        match_report_id=match_report["match_report_id"],
    )
    record = db_session.get(StudyPlan, second["id"])
    record.status = "archived"
    db_session.add(record)
    db_session.commit()

    all_plans = get_data(client.get("/api/study-plans"))
    by_status = get_data(client.get("/api/study-plans?status=archived"))
    by_role = get_data(client.get("/api/study-plans?target_role=Backend%20AI%20Engineer"))
    by_profile = get_data(client.get(f"/api/study-plans?profile_id={profile['id']}"))
    by_match = get_data(
        client.get(
            f"/api/study-plans?match_report_id={match_report['match_report_id']}"
        )
    )

    assert all_plans["total"] == 2
    assert {item["id"] for item in all_plans["items"]} == {first["id"], second["id"]}
    assert [item["id"] for item in by_status["items"]] == [second["id"]]
    assert [item["id"] for item in by_role["items"]] == [first["id"]]
    assert [item["id"] for item in by_profile["items"]] == [first["id"]]
    assert [item["id"] for item in by_match["items"]] == [second["id"]]
    _assert_private_safe(all_plans)


def test_get_study_plan_detail_success_and_missing_error():
    client = make_client()
    plan = _generate_plan(client, weakness_tags=["weak_structure"])

    response = client.get(f"/api/study-plans/{plan['id']}")
    missing = client.get("/api/study-plans/missing_plan")

    assert response.status_code == 200
    detail = get_data(response)
    assert detail["id"] == plan["id"]
    assert detail["phases"] == plan["phases"]
    _assert_private_safe(detail)
    assert missing.status_code == 404
    assert get_error(missing)["code"] == "study_plan_not_found"


def test_update_task_status_success_persists_and_preserves_other_tasks():
    client = make_client()
    plan = _generate_plan(
        client,
        weakness_tags=["weak_structure", "shallow_technical_depth"],
    )
    first_task_id, second_task_id = _first_two_task_ids(plan)
    before_updated_at = plan["updated_at"]

    response = client.patch(
        f"/api/study-plans/{plan['id']}/tasks/{first_task_id}",
        json={"status": "done"},
    )
    detail_response = client.get(f"/api/study-plans/{plan['id']}")

    assert response.status_code == 200
    updated = get_data(response)
    assert updated["updated_at"] != before_updated_at
    statuses = {
        task["task_id"]: task["status"]
        for phase in updated["phases"]
        for task in phase["tasks"]
    }
    assert statuses[first_task_id] == "done"
    assert statuses[second_task_id] == "todo"
    assert get_data(detail_response)["phases"] == updated["phases"]
    _assert_private_safe(updated)


def test_update_task_status_missing_plan_and_task_return_errors():
    client = make_client()
    plan = _generate_plan(client)
    task_id = plan["phases"][0]["tasks"][0]["task_id"]

    missing_plan = client.patch(
        f"/api/study-plans/missing_plan/tasks/{task_id}",
        json={"status": "done"},
    )
    missing_task = client.patch(
        f"/api/study-plans/{plan['id']}/tasks/missing_task",
        json={"status": "done"},
    )

    assert missing_plan.status_code == 404
    assert get_error(missing_plan)["code"] == "study_plan_not_found"
    assert missing_task.status_code == 404
    assert get_error(missing_task)["code"] == "study_plan_task_not_found"


def test_update_task_status_invalid_status_returns_validation_error():
    client = make_client()
    plan = _generate_plan(client)
    task_id = plan["phases"][0]["tasks"][0]["task_id"]

    response = client.patch(
        f"/api/study-plans/{plan['id']}/tasks/{task_id}",
        json={"status": "invalid"},
    )

    assert response.status_code == 422
    assert get_error(response)["code"] == "validation_error"
