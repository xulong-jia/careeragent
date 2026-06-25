from conftest import get_data, get_error, make_client


PRIVATE_TEXT_KEYS = {
    "raw_text",
    "raw_text_preview",
    "resume_text",
    "jd_raw_text",
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


def _create_job(client, raw_text: str | None = None):
    response = client.post(
        "/api/jobs",
        json={
            "company": "Synthetic Interview Co",
            "job_title": "Backend AI Engineer",
            "location": "Shanghai",
            "raw_text": raw_text
            or (
                "We need Python, FastAPI and SQL backend skills. "
                "Docker is preferred. Discuss API design and tradeoffs."
            ),
            "source_url": None,
        },
    )
    assert response.status_code == 201
    return get_data(response)


def _create_resume_version(client, content: bytes | None = None):
    response = client.post(
        "/api/resumes/upload",
        files={
            "file": (
                "interview-source.md",
                content or b"PRIVATE_RESUME_TEXT Python FastAPI project evidence.",
                "text/markdown",
            )
        },
    )
    assert response.status_code == 201
    resume_id = get_data(response)["resume_id"]
    versions = client.get(f"/api/resumes/{resume_id}/versions")
    assert versions.status_code == 200
    return get_data(versions)["items"][0]["resume_version_id"]


def _create_project(client, **overrides):
    payload = {
        "name": "CareerAgent Interview Prep",
        "role": "Backend Engineer",
        "period": "2026-02 to 2026-05",
        "background": "Synthetic local project for interview preparation.",
        "tech_stack": ["Python", "FastAPI"],
        "responsibilities": [
            "Designed FastAPI routes for deterministic interview workflows.",
            "Handled edge cases for source-backed question generation.",
        ],
        "results": [
            "Created reproducible smoke tests with synthetic data only.",
        ],
        "evidence": [
            {
                "type": "test",
                "description": "Synthetic pytest coverage.",
                "source": "local_repo",
            }
        ],
        "status": "active",
    }
    payload.update(overrides)
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 201
    return get_data(response)


def _create_project_rewrite(client, project_id: str, jd_id: str):
    response = client.post(f"/api/projects/{project_id}/rewrite", json={"jd_id": jd_id})
    assert response.status_code == 201
    return get_data(response)


def _generate_questions(client, **overrides):
    job = _create_job(client)
    resume_version_id = _create_resume_version(client)
    payload = {
        "jd_id": job["jd_id"],
        "resume_version_id": resume_version_id,
        "max_questions": 6,
    }
    payload.update(overrides)
    response = client.post("/api/interviews/questions/generate", json=payload)
    return response, payload


def test_generate_questions_success_with_jd_and_resume_version():
    client = make_client()

    response, payload = _generate_questions(client)

    assert response.status_code == 201
    data = get_data(response)
    assert data["questions"]
    assert data["warnings"] == []
    assert data["need_more_info"] == []
    question = data["questions"][0]
    assert question["id"].startswith("interview_question_")
    assert question["user_id"] == "default"
    assert question["jd_id"] == payload["jd_id"]
    assert question["resume_version_id"] == payload["resume_version_id"]
    assert question["difficulty"] in {"easy", "medium", "hard"}
    assert question["source_refs"]
    assert all("preview" in ref for ref in question["source_refs"])
    assert "PRIVATE_RESUME_TEXT" not in response.text
    _assert_private_safe(data)


def test_generate_questions_with_optional_project_creates_project_deep_dive():
    client = make_client()
    job = _create_job(client)
    resume_version_id = _create_resume_version(client)
    project = _create_project(client, resume_version_id=resume_version_id)

    response = client.post(
        "/api/interviews/questions/generate",
        json={
            "jd_id": job["jd_id"],
            "resume_version_id": resume_version_id,
            "project_id": project["id"],
            "max_questions": 6,
        },
    )

    assert response.status_code == 201
    questions = get_data(response)["questions"]
    assert any(question["question_type"] == "project_deep_dive" for question in questions)
    assert any(
        ref["source_type"] == "project" and ref["source_id"] == project["id"]
        for question in questions
        for ref in question["source_refs"]
    )


def test_generate_questions_with_project_rewrite_adds_risk_or_gap_question():
    client = make_client()
    job = _create_job(client)
    resume_version_id = _create_resume_version(client)
    project = _create_project(client, resume_version_id=resume_version_id)
    rewrite = _create_project_rewrite(client, project["id"], job["jd_id"])

    response = client.post(
        "/api/interviews/questions/generate",
        json={
            "jd_id": job["jd_id"],
            "resume_version_id": resume_version_id,
            "project_id": project["id"],
            "project_rewrite_id": rewrite["id"],
            "max_questions": 6,
        },
    )

    assert response.status_code == 201
    questions = get_data(response)["questions"]
    risk_questions = [
        question
        for question in questions
        if question["question_type"] == "risk_or_gap_explanation"
    ]
    assert risk_questions
    assert any(
        ref["source_type"] == "project_rewrite" and ref["source_id"] == rewrite["id"]
        for question in risk_questions
        for ref in question["source_refs"]
    )


def test_generate_questions_returns_clear_errors_for_missing_refs():
    client = make_client()
    job = _create_job(client)
    resume_version_id = _create_resume_version(client)

    missing_job = client.post(
        "/api/interviews/questions/generate",
        json={"jd_id": "missing_jd", "resume_version_id": resume_version_id},
    )
    missing_resume = client.post(
        "/api/interviews/questions/generate",
        json={"jd_id": job["jd_id"], "resume_version_id": "missing_resume_version"},
    )
    missing_project = client.post(
        "/api/interviews/questions/generate",
        json={
            "jd_id": job["jd_id"],
            "resume_version_id": resume_version_id,
            "project_id": "missing_project",
        },
    )
    missing_rewrite = client.post(
        "/api/interviews/questions/generate",
        json={
            "jd_id": job["jd_id"],
            "resume_version_id": resume_version_id,
            "project_rewrite_id": "missing_project_rewrite",
        },
    )

    assert missing_job.status_code == 404
    assert get_error(missing_job)["code"] == "job_not_found"
    assert missing_resume.status_code == 404
    assert get_error(missing_resume)["code"] == "resume_version_not_found"
    assert missing_project.status_code == 404
    assert get_error(missing_project)["code"] == "project_not_found"
    assert missing_rewrite.status_code == 404
    assert get_error(missing_rewrite)["code"] == "project_rewrite_not_found"


def test_generate_questions_rejects_invalid_question_type_and_max_questions():
    client = make_client()
    job = _create_job(client)
    resume_version_id = _create_resume_version(client)

    invalid_type = client.post(
        "/api/interviews/questions/generate",
        json={
            "jd_id": job["jd_id"],
            "resume_version_id": resume_version_id,
            "question_types": ["not_supported"],
        },
    )
    invalid_max = client.post(
        "/api/interviews/questions/generate",
        json={
            "jd_id": job["jd_id"],
            "resume_version_id": resume_version_id,
            "max_questions": 0,
        },
    )

    assert invalid_type.status_code == 422
    assert get_error(invalid_type)["code"] == "validation_error"
    assert invalid_max.status_code == 422
    assert get_error(invalid_max)["code"] == "validation_error"


def test_generate_questions_respects_max_questions_and_includes_technical_depth():
    client = make_client()

    response, _ = _generate_questions(client, max_questions=2)

    assert response.status_code == 201
    questions = get_data(response)["questions"]
    assert len(questions) <= 2
    assert any(question["question_type"] == "technical_depth" for question in questions)


def test_list_questions_filters_by_refs_type_and_difficulty():
    client = make_client()
    job = _create_job(client)
    resume_version_id = _create_resume_version(client)
    project = _create_project(client, resume_version_id=resume_version_id)
    generate = client.post(
        "/api/interviews/questions/generate",
        json={
            "jd_id": job["jd_id"],
            "resume_version_id": resume_version_id,
            "project_id": project["id"],
            "question_types": ["project_deep_dive"],
            "max_questions": 3,
        },
    )
    assert generate.status_code == 201
    created_questions = get_data(generate)["questions"]
    difficulty = created_questions[0]["difficulty"]

    by_jd = client.get("/api/interviews/questions", params={"jd_id": job["jd_id"]})
    by_resume = client.get(
        "/api/interviews/questions",
        params={"resume_version_id": resume_version_id},
    )
    by_project = client.get(
        "/api/interviews/questions", params={"project_id": project["id"]}
    )
    by_type = client.get(
        "/api/interviews/questions", params={"question_type": "project_deep_dive"}
    )
    by_difficulty = client.get(
        "/api/interviews/questions", params={"difficulty": difficulty}
    )

    for response in (by_jd, by_resume, by_project, by_type, by_difficulty):
        assert response.status_code == 200
        data = get_data(response)
        assert data["total"] >= 1
        assert data["items"]
        _assert_private_safe(data)
