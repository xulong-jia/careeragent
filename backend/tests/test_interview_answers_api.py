from conftest import get_data, get_error, make_client


PRIVATE_TEXT_KEYS = {
    "raw_text",
    "resume_text",
    "jd_raw_text",
    "full_text",
    "source_text",
    "answer_text",
}


def _assert_private_safe(value):
    if isinstance(value, dict):
        assert PRIVATE_TEXT_KEYS.isdisjoint(value.keys())
        for child in value.values():
            _assert_private_safe(child)
    elif isinstance(value, list):
        for child in value:
            _assert_private_safe(child)


def _create_job(client):
    response = client.post(
        "/api/jobs",
        json={
            "company": "Synthetic Answer Co",
            "job_title": "Backend AI Engineer",
            "location": "Shanghai",
            "raw_text": (
                "We need Python, FastAPI and SQL backend skills. "
                "Discuss API design, testing, workflow quality and risk tradeoffs."
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
                "answer-source.md",
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


def _create_project(client, resume_version_id: str):
    response = client.post(
        "/api/projects",
        json={
            "name": "Interview Answer Workbench",
            "role": "Backend Engineer",
            "period": "2026-02 to 2026-05",
            "background": "Synthetic project facts for answer scoring.",
            "tech_stack": ["Python", "FastAPI", "SQL"],
            "responsibilities": [
                "Designed FastAPI routes with schema validation and pytest coverage.",
            ],
            "results": [
                "Created reproducible deterministic tests with source refs.",
            ],
            "evidence": [
                {"type": "test", "description": "pytest smoke coverage"},
            ],
            "resume_version_id": resume_version_id,
            "status": "active",
        },
    )
    assert response.status_code == 201
    return get_data(response)


def _create_question(client, *, with_project: bool = False):
    job = _create_job(client)
    resume_version_id = _create_resume_version(client)
    payload = {
        "jd_id": job["jd_id"],
        "resume_version_id": resume_version_id,
        "max_questions": 4,
    }
    project = None
    if with_project:
        project = _create_project(client, resume_version_id)
        payload["project_id"] = project["id"]
    response = client.post("/api/interviews/questions/generate", json=payload)
    assert response.status_code == 201
    question = get_data(response)["questions"][0]
    return question, job, resume_version_id, project


def _submit_answer(client, question_id: str, answer_text: str | None = None):
    response = client.post(
        "/api/interviews/answers",
        json={
            "question_id": question_id,
            "answer_text": answer_text
            or (
                "1. Background: I built a FastAPI API with schema validation.\n"
                "2. Action: I added database tests and pytest evidence.\n"
                "3. Result: The workflow had clear source refs and risk checks."
            ),
        },
    )
    assert response.status_code == 201
    return get_data(response)


def test_submit_answer_success_returns_preview_without_full_answer_text():
    client = make_client()
    question, _, _, _ = _create_question(client)
    answer_text = (
        "1. Background: I built a FastAPI API with schema validation.\n"
        "2. Action: I added database tests and pytest evidence.\n"
        "3. Result: The workflow had clear source refs and risk checks."
    )

    response = client.post(
        "/api/interviews/answers",
        json={"question_id": question["id"], "answer_text": answer_text},
    )

    assert response.status_code == 201
    data = get_data(response)
    assert data["id"].startswith("interview_answer_")
    assert data["question_id"] == question["id"]
    assert data["user_id"] == "default"
    assert len(data["answer_text_preview"]) <= 180
    assert data["answer_text_preview"].startswith("1. Background")
    assert "pytest evidence" in data["answer_text_preview"]
    assert data["scores"] == {}
    assert data["feedback"] is None
    assert data["weakness_tags"] == []
    assert "answer_text" not in data
    assert answer_text not in response.text
    assert "PRIVATE_RESUME_TEXT" not in response.text
    _assert_private_safe(data)


def test_submit_answer_rejects_missing_question_and_empty_answer():
    client = make_client()
    question, _, _, _ = _create_question(client)

    missing_question = client.post(
        "/api/interviews/answers",
        json={"question_id": "missing_question", "answer_text": "Valid text"},
    )
    empty_answer = client.post(
        "/api/interviews/answers",
        json={"question_id": question["id"], "answer_text": "   "},
    )
    blank_answer = client.post(
        "/api/interviews/answers",
        json={"question_id": question["id"], "answer_text": ""},
    )

    assert missing_question.status_code == 404
    assert get_error(missing_question)["code"] == "interview_question_not_found"
    assert empty_answer.status_code == 400
    assert get_error(empty_answer)["code"] == "interview_answer_validation_error"
    assert blank_answer.status_code == 400
    assert get_error(blank_answer)["code"] == "interview_answer_validation_error"


def test_list_answers_filters_by_question_jd_resume_version_and_project():
    client = make_client()
    question, job, resume_version_id, project = _create_question(client, with_project=True)
    answer = _submit_answer(client, question["id"])

    by_question = client.get(
        "/api/interviews/answers", params={"question_id": question["id"]}
    )
    by_jd = client.get("/api/interviews/answers", params={"jd_id": job["jd_id"]})
    by_resume = client.get(
        "/api/interviews/answers",
        params={"resume_version_id": resume_version_id},
    )
    by_project = client.get(
        "/api/interviews/answers", params={"project_id": project["id"]}
    )

    for response in (by_question, by_jd, by_resume, by_project):
        assert response.status_code == 200
        data = get_data(response)
        assert data["total"] == 1
        assert data["items"][0]["id"] == answer["id"]
        assert "answer_text" not in data["items"][0]
        assert "PRIVATE_RESUME_TEXT" not in response.text
        _assert_private_safe(data)
