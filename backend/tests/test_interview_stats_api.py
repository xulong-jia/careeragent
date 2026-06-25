from conftest import get_data, make_client


PRIVATE_TEXT_KEYS = {
    "raw_text",
    "raw_text_preview",
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
            "company": "Synthetic Stats Co",
            "job_title": "Backend AI Engineer",
            "location": "Shanghai",
            "raw_text": (
                "PRIVATE_JD_TEXT We need Python, FastAPI, SQL, testing, "
                "workflow quality and risk control."
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
                "stats-source.md",
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


def _generate_questions(client):
    job = _create_job(client)
    resume_version_id = _create_resume_version(client)
    response = client.post(
        "/api/interviews/questions/generate",
        json={
            "jd_id": job["jd_id"],
            "resume_version_id": resume_version_id,
            "max_questions": 4,
        },
    )
    assert response.status_code == 201
    return get_data(response)["questions"]


def _submit_answer(client, question_id: str, answer_text: str = "vague answer"):
    response = client.post(
        "/api/interviews/answers",
        json={"question_id": question_id, "answer_text": answer_text},
    )
    assert response.status_code == 201
    return get_data(response)


def test_interview_stats_empty():
    client = make_client()

    response = client.get("/api/interviews/stats")

    assert response.status_code == 200
    data = get_data(response)
    assert data == {
        "total_questions": 0,
        "total_answers": 0,
        "scored_answers": 0,
        "latest_average_score": None,
        "latest_weakness_tags": [],
        "by_question_type": {},
        "by_difficulty": {},
    }


def test_interview_stats_after_generated_questions():
    client = make_client()
    questions = _generate_questions(client)

    response = client.get("/api/interviews/stats")

    assert response.status_code == 200
    data = get_data(response)
    assert data["total_questions"] == len(questions)
    assert data["total_answers"] == 0
    assert data["scored_answers"] == 0
    assert data["latest_average_score"] is None
    assert data["latest_weakness_tags"] == []
    assert sum(data["by_question_type"].values()) == len(questions)
    assert sum(data["by_difficulty"].values()) == len(questions)
    assert questions[0]["question_type"] in data["by_question_type"]
    assert questions[0]["difficulty"] in data["by_difficulty"]


def test_interview_stats_after_submitted_answer_without_score():
    client = make_client()
    question = _generate_questions(client)[0]
    answer = _submit_answer(client, question["id"])

    response = client.get("/api/interviews/stats")

    assert response.status_code == 200
    data = get_data(response)
    assert data["total_answers"] == 1
    assert data["scored_answers"] == 0
    assert data["latest_average_score"] is None
    assert data["latest_weakness_tags"] == []
    assert "answer_text" not in answer


def test_interview_stats_after_scored_answer_is_private_and_uses_latest_score():
    client = make_client()
    question = _generate_questions(client)[0]
    answer = _submit_answer(client, question["id"], "million users revenue")

    score_response = client.post(f"/api/interviews/answers/{answer['id']}/score")
    assert score_response.status_code == 200
    scored = get_data(score_response)

    response = client.get("/api/interviews/stats")

    assert response.status_code == 200
    data = get_data(response)
    assert data["total_questions"] >= 1
    assert data["total_answers"] == 1
    assert data["scored_answers"] == 1
    assert data["latest_average_score"] == scored["scores"]["overall_average"]
    assert data["latest_weakness_tags"] == scored["weakness_tags"]
    assert data["latest_weakness_tags"]
    assert "PRIVATE_RESUME_TEXT" not in response.text
    assert "PRIVATE_JD_TEXT" not in response.text
    assert "million users revenue" not in response.text
    _assert_private_safe(data)
