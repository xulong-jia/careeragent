from conftest import get_data, get_error, make_client


PRIVATE_TEXT_KEYS = {
    "raw_text",
    "raw_text_preview",
    "resume_text",
    "jd_raw_text",
    "answer_text",
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


def _assert_plan_shape(plan):
    assert plan["id"].startswith("study_plan_")
    assert plan["user_id"] == "default"
    assert plan["target_role"]
    assert plan["status"] == "active"
    assert plan["created_at"]
    assert plan["updated_at"]
    assert isinstance(plan["source_refs"], list)
    assert plan["phases"]
    for phase in plan["phases"]:
        assert phase["phase_id"].startswith("phase_")
        assert phase["phase"]
        assert phase["goal"]
        assert phase["tasks"]
        assert phase["resources"]
        assert phase["deliverables"]
        assert phase["acceptance_criteria"]
        for task in phase["tasks"]:
            assert task["task_id"].startswith("task_")
            assert task["title"]
            assert task["description"]
            assert task["source_gap"]
            assert task["priority"] in {"high", "medium", "low"}
            assert task["status"] == "todo"
            assert task["acceptance_criteria"]
            assert "source_refs" in task
    _assert_private_safe(plan)


def _create_profile(client):
    response = client.post(
        "/api/profiles",
        json={
            "target_roles": ["Backend AI Engineer"],
            "target_industries": ["Enterprise Software"],
            "target_locations": ["Shanghai"],
            "skill_map": {
                "backend": ["FastAPI"],
                "missing": ["Kubernetes"],
            },
            "preferences": {},
            "source_resume_version_id": None,
        },
    )
    assert response.status_code == 201
    return get_data(response)


def _create_job(client):
    response = client.post(
        "/api/jobs",
        json={
            "company": "Synthetic Study Co",
            "job_title": "Backend AI Engineer",
            "location": "Shanghai",
            "raw_text": (
                "PRIVATE_JD_TEXT We need Python, FastAPI, SQL, Docker, "
                "Kubernetes, testing, risk control and stakeholder communication."
            ),
            "source_url": None,
        },
    )
    assert response.status_code == 201
    return get_data(response)


def _create_resume_version(client):
    response = client.post(
        "/api/resumes/upload",
        files={
            "file": (
                "study-source.md",
                b"PRIVATE_RESUME_TEXT Python FastAPI SQL testing project.",
                "text/markdown",
            )
        },
    )
    assert response.status_code == 201
    resume_id = get_data(response)["resume_id"]
    versions = client.get(f"/api/resumes/{resume_id}/versions")
    assert versions.status_code == 200
    return get_data(versions)["items"][0]["resume_version_id"]


def _create_match_report(client):
    resume_version_id = _create_resume_version(client)
    job = _create_job(client)
    response = client.post(
        "/api/matches/run",
        json={"resume_version_id": resume_version_id, "jd_id": job["jd_id"]},
    )
    assert response.status_code == 201
    return get_data(response)


def _create_project_rewrite(client):
    profile = _create_profile(client)
    resume_version_id = _create_resume_version(client)
    job = _create_job(client)
    match_response = client.post(
        "/api/matches/run",
        json={"resume_version_id": resume_version_id, "jd_id": job["jd_id"]},
    )
    assert match_response.status_code == 201
    match_report = get_data(match_response)
    project_response = client.post(
        "/api/projects",
        json={
            "profile_id": profile["id"],
            "resume_version_id": resume_version_id,
            "name": "Synthetic Backend Platform",
            "role": "Backend Engineer",
            "period": "2026-01 to 2026-05",
            "background": "Synthetic local learning project.",
            "tech_stack": ["Python", "FastAPI"],
            "responsibilities": ["Built API workflows for local job preparation."],
            "results": ["Improved local test coverage in synthetic runs."],
            "evidence": [],
            "status": "active",
        },
    )
    assert project_response.status_code == 201
    project = get_data(project_response)
    rewrite_response = client.post(
        f"/api/projects/{project['id']}/rewrite",
        json={
            "jd_id": job["jd_id"],
            "resume_version_id": resume_version_id,
            "match_report_id": match_report["match_report_id"],
            "profile_id": profile["id"],
        },
    )
    assert rewrite_response.status_code == 201
    return get_data(rewrite_response)


def _create_scored_interview_answer(client):
    resume_version_id = _create_resume_version(client)
    job = _create_job(client)
    questions_response = client.post(
        "/api/interviews/questions/generate",
        json={
            "jd_id": job["jd_id"],
            "resume_version_id": resume_version_id,
            "max_questions": 3,
        },
    )
    assert questions_response.status_code == 201
    question = get_data(questions_response)["questions"][0]
    answer_text = "PRIVATE_ANSWER_TEXT launched million users revenue"
    answer_response = client.post(
        "/api/interviews/answers",
        json={"question_id": question["id"], "answer_text": answer_text},
    )
    assert answer_response.status_code == 201
    answer = get_data(answer_response)
    score_response = client.post(f"/api/interviews/answers/{answer['id']}/score")
    assert score_response.status_code == 200
    return get_data(score_response)


def test_generate_study_plan_from_target_role_only_creates_basic_manual_gap_plan():
    client = make_client()

    response = client.post(
        "/api/study-plans/generate",
        json={"target_role": "Backend AI Engineer"},
    )

    assert response.status_code == 201
    plan = get_data(response)
    _assert_plan_shape(plan)
    assert plan["target_role"] == "Backend AI Engineer"
    assert any(
        task["source_gap"] == "manual_gap_review"
        for phase in plan["phases"]
        for task in phase["tasks"]
    )


def test_generate_study_plan_can_infer_target_role_from_profile_and_skill_map():
    client = make_client()
    profile = _create_profile(client)

    response = client.post(
        "/api/study-plans/generate",
        json={"profile_id": profile["id"]},
    )

    assert response.status_code == 201
    plan = get_data(response)
    _assert_plan_shape(plan)
    assert plan["profile_id"] == profile["id"]
    assert plan["target_role"] == "Backend AI Engineer"
    assert any(ref["source_type"] == "profile" for ref in plan["source_refs"])


def test_generate_study_plan_from_match_gaps():
    client = make_client()
    match_report = _create_match_report(client)

    response = client.post(
        "/api/study-plans/generate",
        json={
            "target_role": "Backend AI Engineer",
            "match_report_id": match_report["match_report_id"],
        },
    )

    assert response.status_code == 201
    plan = get_data(response)
    _assert_plan_shape(plan)
    assert plan["match_report_id"] == match_report["match_report_id"]
    assert any(
        ref["source_type"] == "match_report" for ref in plan["source_refs"]
    )
    assert any(
        "match" in task["source_gap"]
        for phase in plan["phases"]
        for task in phase["tasks"]
    )
    assert "PRIVATE_RESUME_TEXT" not in response.text
    assert "PRIVATE_JD_TEXT" not in response.text


def test_generate_study_plan_from_project_rewrite_missing_points():
    client = make_client()
    rewrite = _create_project_rewrite(client)

    response = client.post(
        "/api/study-plans/generate",
        json={
            "target_role": "Backend AI Engineer",
            "project_rewrite_id": rewrite["id"],
        },
    )

    assert response.status_code == 201
    plan = get_data(response)
    _assert_plan_shape(plan)
    assert plan["project_rewrite_id"] == rewrite["id"]
    assert any(
        ref["source_type"] == "project_rewrite" for ref in plan["source_refs"]
    )
    assert any(
        task["source_gap"] in {"missing_required_skill", "missing_evidence"}
        for phase in plan["phases"]
        for task in phase["tasks"]
    )


def test_generate_study_plan_from_interview_weakness_tags_is_preview_safe():
    client = make_client()
    answer = _create_scored_interview_answer(client)

    response = client.post(
        "/api/study-plans/generate",
        json={
            "target_role": "Backend AI Engineer",
            "interview_answer_ids": [answer["id"]],
        },
    )

    assert response.status_code == 201
    plan = get_data(response)
    _assert_plan_shape(plan)
    assert any(
        ref["source_type"] == "interview_answer" for ref in plan["source_refs"]
    )
    assert any(
        task["source_gap"] in set(answer["weakness_tags"])
        for phase in plan["phases"]
        for task in phase["tasks"]
    )
    assert "PRIVATE_ANSWER_TEXT" not in response.text


def test_generate_study_plan_from_request_weakness_tags():
    client = make_client()

    response = client.post(
        "/api/study-plans/generate",
        json={
            "target_role": "Backend AI Engineer",
            "weakness_tags": ["weak_structure", "shallow_technical_depth"],
        },
    )

    assert response.status_code == 201
    plan = get_data(response)
    _assert_plan_shape(plan)
    task_gaps = {
        task["source_gap"]
        for phase in plan["phases"]
        for task in phase["tasks"]
    }
    assert {"weak_structure", "shallow_technical_depth"}.issubset(task_gaps)


def test_generate_study_plan_missing_refs_return_errors():
    client = make_client()

    missing_profile = client.post(
        "/api/study-plans/generate",
        json={"target_role": "Backend AI Engineer", "profile_id": "missing_profile"},
    )
    missing_match = client.post(
        "/api/study-plans/generate",
        json={"target_role": "Backend AI Engineer", "match_report_id": "missing_match"},
    )
    missing_rewrite = client.post(
        "/api/study-plans/generate",
        json={
            "target_role": "Backend AI Engineer",
            "project_rewrite_id": "missing_rewrite",
        },
    )
    missing_answer = client.post(
        "/api/study-plans/generate",
        json={
            "target_role": "Backend AI Engineer",
            "interview_answer_ids": ["missing_answer"],
        },
    )

    assert missing_profile.status_code == 404
    assert get_error(missing_profile)["code"] == "profile_not_found"
    assert missing_match.status_code == 404
    assert get_error(missing_match)["code"] == "match_report_not_found"
    assert missing_rewrite.status_code == 404
    assert get_error(missing_rewrite)["code"] == "project_rewrite_not_found"
    assert missing_answer.status_code == 404
    assert get_error(missing_answer)["code"] == "interview_answer_not_found"


def test_generate_study_plan_requires_target_role_when_it_cannot_be_inferred():
    client = make_client()

    response = client.post("/api/study-plans/generate", json={})

    assert response.status_code == 400
    assert get_error(response)["code"] == "study_plan_target_role_required"
