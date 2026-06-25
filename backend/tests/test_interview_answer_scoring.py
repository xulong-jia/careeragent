from conftest import get_data, get_error, make_client


SCORE_DIMENSIONS = {
    "structure",
    "technical_depth",
    "business_understanding",
    "evidence",
    "clarity",
    "risk_control",
    "overall_average",
}


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
            "company": "Synthetic Scoring Co",
            "job_title": "Backend AI Engineer",
            "location": "Shanghai",
            "raw_text": (
                "We need Python, FastAPI, SQL and testing skills. "
                "The role requires API design, workflow quality and risk control."
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
                "scoring-source.md",
                b"PRIVATE_RESUME_TEXT Python FastAPI SQL pytest project evidence.",
                "text/markdown",
            )
        },
    )
    assert response.status_code == 201
    resume_id = get_data(response)["resume_id"]
    versions = client.get(f"/api/resumes/{resume_id}/versions")
    assert versions.status_code == 200
    return get_data(versions)["items"][0]["resume_version_id"]


def _create_question(client):
    job = _create_job(client)
    resume_version_id = _create_resume_version(client)
    response = client.post(
        "/api/interviews/questions/generate",
        json={
            "jd_id": job["jd_id"],
            "resume_version_id": resume_version_id,
            "question_types": ["technical_depth"],
            "max_questions": 2,
        },
    )
    assert response.status_code == 201
    return get_data(response)["questions"][0]


def _submit_answer(client, question_id: str, answer_text: str):
    response = client.post(
        "/api/interviews/answers",
        json={"question_id": question_id, "answer_text": answer_text},
    )
    assert response.status_code == 201
    return get_data(response)


def _score_answer(client, answer_id: str):
    response = client.post(f"/api/interviews/answers/{answer_id}/score", json={})
    assert response.status_code == 200
    return get_data(response)


def test_score_answer_success_updates_scores_feedback_and_weakness_tags():
    client = make_client()
    question = _create_question(client)
    answer = _submit_answer(
        client,
        question["id"],
        (
            "1. Background: I owned a FastAPI API workflow.\n"
            "2. Action: I designed schema validation, database persistence, "
            "pytest testing and Docker smoke checks.\n"
            "3. Result: I used evaluation logs and before/after checks as evidence, "
            "and I would be honest about unsupported claims."
        ),
    )

    scored = _score_answer(client, answer["id"])

    assert scored["id"] == answer["id"]
    assert set(scored["scores"]) == SCORE_DIMENSIONS
    for key, value in scored["scores"].items():
        if key != "overall_average":
            assert 0 <= value <= 5
    assert 0 <= scored["scores"]["overall_average"] <= 5
    assert scored["feedback"]
    assert isinstance(scored["weakness_tags"], list)
    assert "answer_text" not in scored
    assert "PRIVATE_RESUME_TEXT" not in str(scored)
    _assert_private_safe(scored)


def test_score_answer_generates_weakness_tags_for_short_generic_answer():
    client = make_client()
    question = _create_question(client)
    answer = _submit_answer(client, question["id"], "I did it well.")

    scored = _score_answer(client, answer["id"])

    assert scored["scores"]["structure"] <= 2
    assert scored["scores"]["technical_depth"] <= 2
    assert scored["scores"]["evidence"] <= 2
    assert {"weak_structure", "shallow_technical_depth", "missing_evidence"} & set(
        scored["weakness_tags"]
    )
    assert "补充已有项目事实" in scored["feedback"]


def test_score_answer_risk_control_catches_overclaim():
    client = make_client()
    question = _create_question(client)
    answer = _submit_answer(
        client,
        question["id"],
        (
            "I launched it to production with million users, revenue growth, "
            "commercial accuracy and 上线 收益 百万用户 准确率, but I have no evidence."
        ),
    )

    scored = _score_answer(client, answer["id"])

    assert scored["scores"]["risk_control"] <= 2
    assert "overclaim_risk" in scored["weakness_tags"]


def test_score_answer_rewards_expected_points_and_evidence_terms():
    client = make_client()
    question = _create_question(client)
    answer = _submit_answer(
        client,
        question["id"],
        (
            "First, implementation: I built the FastAPI API with schema and database "
            "persistence. Second, tradeoff: I chose deterministic validation for "
            "quality and risk control. Third, evidence: pytest tests, evaluation logs, "
            "before/after checks and source refs showed the workflow behavior."
        ),
    )

    scored = _score_answer(client, answer["id"])

    assert scored["scores"]["technical_depth"] >= 3
    assert scored["scores"]["evidence"] >= 3
    assert scored["scores"]["business_understanding"] >= 3


def test_score_answer_missing_answer_returns_error():
    client = make_client()

    response = client.post("/api/interviews/answers/missing_answer/score", json={})

    assert response.status_code == 404
    assert get_error(response)["code"] == "interview_answer_not_found"


def test_score_feedback_does_not_invent_metrics_or_experience():
    client = make_client()
    question = _create_question(client)
    answer = _submit_answer(
        client,
        question["id"],
        "I can explain FastAPI schema validation, pytest evidence and risk control.",
    )

    scored = _score_answer(client, answer["id"])

    forbidden = ["million users", "revenue", "accuracy", "commercial", "上线", "收益"]
    feedback_lower = scored["feedback"].lower()
    assert all(term.lower() not in feedback_lower for term in forbidden)
