from conftest import get_data, make_client
from app.models.study_plan import StudyPlan
from test_study_plan_generate_api import _assert_private_safe


def _generate_plan(client, target_role="Backend AI Engineer", weakness_tags=None):
    response = client.post(
        "/api/study-plans/generate",
        json={
            "target_role": target_role,
            "weakness_tags": weakness_tags or ["weak_structure", "overclaim_risk"],
        },
    )
    assert response.status_code == 201
    return get_data(response)


def _patch_task(client, plan_id: str, task_id: str, status: str):
    response = client.patch(
        f"/api/study-plans/{plan_id}/tasks/{task_id}",
        json={"status": status},
    )
    assert response.status_code == 200
    return get_data(response)


def test_study_plan_stats_empty():
    client = make_client()

    response = client.get("/api/study-plans/stats")

    assert response.status_code == 200
    assert get_data(response) == {
        "total_plans": 0,
        "active_plans": 0,
        "completed_plans": 0,
        "archived_plans": 0,
        "pending_tasks": 0,
        "blocked_tasks": 0,
        "done_tasks": 0,
        "in_progress_tasks": 0,
        "skipped_tasks": 0,
        "latest_plan_id": None,
        "latest_target_role": None,
    }


def test_study_plan_stats_after_one_active_plan_is_private():
    client = make_client()
    plan = _generate_plan(client)
    task_count = sum(len(phase["tasks"]) for phase in plan["phases"])

    response = client.get("/api/study-plans/stats")

    assert response.status_code == 200
    data = get_data(response)
    assert data["total_plans"] == 1
    assert data["active_plans"] == 1
    assert data["completed_plans"] == 0
    assert data["archived_plans"] == 0
    assert data["pending_tasks"] == task_count
    assert data["done_tasks"] == 0
    assert data["blocked_tasks"] == 0
    assert data["latest_plan_id"] == plan["id"]
    assert data["latest_target_role"] == "Backend AI Engineer"
    assert "source_refs" not in data
    _assert_private_safe(data)


def test_study_plan_stats_count_task_statuses():
    client = make_client()
    plan = _generate_plan(
        client,
        weakness_tags=[
            "weak_structure",
            "shallow_technical_depth",
            "missing_evidence",
            "overclaim_risk",
        ],
    )
    task_ids = [
        task["task_id"]
        for phase in plan["phases"]
        for task in phase["tasks"]
    ]
    assert len(task_ids) >= 4
    _patch_task(client, plan["id"], task_ids[0], "done")
    _patch_task(client, plan["id"], task_ids[1], "blocked")
    _patch_task(client, plan["id"], task_ids[2], "in_progress")
    _patch_task(client, plan["id"], task_ids[3], "skipped")

    response = client.get("/api/study-plans/stats")

    assert response.status_code == 200
    data = get_data(response)
    assert data["done_tasks"] == 1
    assert data["blocked_tasks"] == 1
    assert data["in_progress_tasks"] == 1
    assert data["skipped_tasks"] == 1
    assert data["pending_tasks"] == len(task_ids) - 4


def test_study_plan_stats_counts_plan_statuses_and_latest_plan(db_session):
    client = make_client()
    first = _generate_plan(client, target_role="Backend AI Engineer")
    second = _generate_plan(client, target_role="Data Engineer")
    first_record = db_session.get(StudyPlan, first["id"])
    first_record.status = "completed"
    second_record = db_session.get(StudyPlan, second["id"])
    second_record.status = "archived"
    db_session.add(first_record)
    db_session.add(second_record)
    db_session.commit()

    response = client.get("/api/study-plans/stats")

    assert response.status_code == 200
    data = get_data(response)
    assert data["total_plans"] == 2
    assert data["active_plans"] == 0
    assert data["completed_plans"] == 1
    assert data["archived_plans"] == 1
    assert data["latest_plan_id"] == second["id"]
    assert data["latest_target_role"] == "Data Engineer"
