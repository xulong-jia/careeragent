from app.agents import state
from app.models.agent import AgentRun
from app.models.job import JobDescription, JobProfile
from app.models.resume import Resume, ResumeVersion
from conftest import get_data, get_error, make_client


PRIVATE_TEXT_KEYS = {"raw_text", "jd_raw_text", "chunk_text"}


def _create_resume_with_version(db_session, *, resume_id="resume_api_0001"):
    resume = Resume(
        id=resume_id,
        title="Synthetic resume",
        original_filename="synthetic_resume.md",
        file_type="markdown",
        source_file_hash="synthetic-hash",
        status="active",
    )
    version = ResumeVersion(
        id=f"{resume_id}_version_0001",
        resume_id=resume_id,
        version_name="Initial version",
        version_number=1,
        raw_text="Synthetic resume text with Python and FastAPI.",
        raw_text_preview="Synthetic resume text with Python and FastAPI.",
        structured_resume={"skills": {"backend": ["Python", "FastAPI"]}},
        extraction_status="extracted",
        extraction_method="synthetic",
        extraction_warnings=[],
        risk_flags=[],
        status="active",
    )
    db_session.add(resume)
    db_session.add(version)
    db_session.commit()
    return resume, version


def _create_job_with_profile(db_session, *, jd_id="jd_api_0001"):
    job = JobDescription(
        id=jd_id,
        company="Synthetic Company",
        job_title="Backend Engineer",
        location="Remote",
        raw_text="Synthetic JD requiring Python and FastAPI.",
        status="active",
    )
    profile = JobProfile(
        id=f"profile_{jd_id}_0001",
        jd_id=jd_id,
        profile_version=1,
        role_category="Python Backend Developer",
        required_skills=["Python", "FastAPI"],
        preferred_skills=[],
        responsibilities=["Build APIs"],
        business_scenarios=[],
        hidden_requirements=[],
        interview_focus=[],
        risk_level="low",
        summary="Synthetic job profile.",
    )
    db_session.add(job)
    db_session.add(profile)
    db_session.commit()
    return job, profile


def _assert_refs_are_private_safe(value):
    if isinstance(value, dict):
        assert PRIVATE_TEXT_KEYS.isdisjoint(value.keys())
        for child in value.values():
            _assert_refs_are_private_safe(child)
    elif isinstance(value, list):
        for child in value:
            _assert_refs_are_private_safe(child)


def test_create_agent_run_successful_workflow(db_session):
    client = make_client()
    _, version = _create_resume_with_version(db_session)
    _create_job_with_profile(db_session)

    response = client.post(
        "/api/agents/runs",
        json={
            "workflow_name": state.WORKFLOW_JOB_APPLICATION_PREPARATION,
            "resume_version_id": version.id,
            "jd_id": "jd_api_0001",
            "use_rag": False,
        },
    )

    assert response.status_code == 201
    data = get_data(response)
    assert data["run"]["id"].startswith("agent_run_")
    assert data["run"]["status"] == state.RUN_STATUS_COMPLETED
    assert data["run"]["output_refs"]["resume_version_id"] == version.id
    assert data["run"]["output_refs"]["jd_id"] == "jd_api_0001"
    assert data["steps_count"] == 6
    _assert_refs_are_private_safe(data["run"]["input_refs"])
    _assert_refs_are_private_safe(data["run"]["output_refs"])


def test_create_agent_run_missing_inputs_returns_need_more_info():
    client = make_client()

    response = client.post(
        "/api/agents/runs",
        json={"workflow_name": state.WORKFLOW_JOB_APPLICATION_PREPARATION},
    )

    assert response.status_code == 201
    data = get_data(response)
    run = data["run"]
    assert run["status"] == state.RUN_STATUS_NEED_MORE_INFO
    assert {slot["name"] for slot in run["missing_slots"]} == {"resume", "jd_id"}
    assert data["steps_count"] == 1
    assert run["questions"]


def test_create_agent_run_unsupported_workflow_returns_safe_error():
    client = make_client()

    response = client.post(
        "/api/agents/runs",
        json={"workflow_name": "unsupported_workflow"},
    )

    assert response.status_code == 400
    error = get_error(response)
    assert error["code"] == state.ERROR_AGENT_WORKFLOW_NOT_SUPPORTED
    assert "raw_text" not in error["message"]


def test_list_agent_runs_supports_filters_and_limit(db_session):
    client = make_client()
    _, version = _create_resume_with_version(db_session)
    _create_job_with_profile(db_session)
    completed = get_data(
        client.post(
            "/api/agents/runs",
            json={
                "workflow_name": state.WORKFLOW_JOB_APPLICATION_PREPARATION,
                "resume_version_id": version.id,
                "jd_id": "jd_api_0001",
                "use_rag": False,
            },
        )
    )["run"]
    need_more_info = get_data(
        client.post(
            "/api/agents/runs",
            json={"workflow_name": state.WORKFLOW_JOB_APPLICATION_PREPARATION},
        )
    )["run"]

    list_response = client.get("/api/agents/runs")
    assert list_response.status_code == 200
    listed = get_data(list_response)
    assert listed["total"] == 2
    assert listed["items"][0]["id"] == need_more_info["id"]
    assert listed["items"][1]["id"] == completed["id"]

    filtered_response = client.get(
        "/api/agents/runs",
        params={
            "workflow_name": state.WORKFLOW_JOB_APPLICATION_PREPARATION,
            "status": state.RUN_STATUS_COMPLETED,
            "limit": 1,
        },
    )
    assert filtered_response.status_code == 200
    filtered = get_data(filtered_response)
    assert filtered["total"] == 1
    assert filtered["items"][0]["status"] == state.RUN_STATUS_COMPLETED


def test_get_agent_run_detail_and_ordered_steps(db_session):
    client = make_client()
    _, version = _create_resume_with_version(db_session)
    _create_job_with_profile(db_session)
    run = get_data(
        client.post(
            "/api/agents/runs",
            json={
                "workflow_name": state.WORKFLOW_JOB_APPLICATION_PREPARATION,
                "resume_version_id": version.id,
                "jd_id": "jd_api_0001",
                "use_rag": False,
            },
        )
    )["run"]

    detail_response = client.get(f"/api/agents/runs/{run['id']}")
    assert detail_response.status_code == 200
    detail = get_data(detail_response)
    assert detail["run"]["id"] == run["id"]
    assert detail["steps_count"] == 6
    assert "steps" not in detail["run"]

    steps_response = client.get(f"/api/agents/runs/{run['id']}/steps")
    assert steps_response.status_code == 200
    steps_data = get_data(steps_response)
    assert steps_data["total"] == 6
    assert [step["step_order"] for step in steps_data["steps"]] == [1, 2, 3, 4, 5, 6]
    assert [step["step_name"] for step in steps_data["steps"]] == [
        "validate_inputs",
        "load_resume_version",
        "load_job_profile",
        "run_match_report",
        "rag_search",
        "build_final_summary",
    ]
    rag_step = [step for step in steps_data["steps"] if step["step_name"] == "rag_search"][0]
    assert rag_step["status"] == state.STEP_STATUS_SKIPPED
    for step in steps_data["steps"]:
        _assert_refs_are_private_safe(step["input_refs"])
        _assert_refs_are_private_safe(step["output_refs"])


def test_create_agent_run_with_rag_source_refs(db_session):
    client = make_client()
    _, version = _create_resume_with_version(db_session)
    _create_job_with_profile(db_session)
    document_response = client.post(
        "/api/rag/documents",
        json={
            "title": "Synthetic Agent RAG Notes",
            "source_type": "manual",
            "raw_text": "Interview preparation should mention Python API ownership.",
            "metadata": {"fixture": "synthetic-agent"},
        },
    )
    document = get_data(document_response)
    index_response = client.post(
        f"/api/rag/documents/{document['doc_id']}/index",
        json={"max_chars": 120},
    )
    assert index_response.status_code == 200

    run_response = client.post(
        "/api/agents/runs",
        json={
            "workflow_name": state.WORKFLOW_JOB_APPLICATION_PREPARATION,
            "resume_version_id": version.id,
            "jd_id": "jd_api_0001",
            "use_rag": True,
            "rag_query": "Python API ownership interview preparation",
        },
    )

    assert run_response.status_code == 201
    run = get_data(run_response)["run"]
    assert run["status"] == state.RUN_STATUS_COMPLETED
    assert run["output_refs"]["rag_source_count"] >= 1

    steps = get_data(client.get(f"/api/agents/runs/{run['id']}/steps"))["steps"]
    rag_step = [step for step in steps if step["step_name"] == "rag_search"][0]
    assert rag_step["status"] == state.STEP_STATUS_COMPLETED
    assert rag_step["output_refs"]["source_count"] >= 1
    assert "snippet" not in rag_step["output_refs"]


def test_missing_agent_run_returns_404():
    client = make_client()

    detail_response = client.get("/api/agents/runs/missing-run")
    assert detail_response.status_code == 404
    assert get_error(detail_response)["code"] == "agent_run_not_found"

    steps_response = client.get("/api/agents/runs/missing-run/steps")
    assert steps_response.status_code == 404
    assert get_error(steps_response)["code"] == "agent_run_not_found"


def test_agent_api_response_does_not_include_private_text_keys(db_session):
    client = make_client()
    _, version = _create_resume_with_version(db_session)
    _create_job_with_profile(db_session)

    response = client.post(
        "/api/agents/runs",
        json={
            "workflow_name": state.WORKFLOW_JOB_APPLICATION_PREPARATION,
            "resume_version_id": version.id,
            "jd_id": "jd_api_0001",
            "use_rag": False,
        },
    )

    payload = response.json()
    assert response.status_code == 201
    serialized = str(payload)
    assert "jd_raw_text" not in serialized
    assert "chunk_text" not in serialized
    assert "Synthetic resume text with Python and FastAPI." not in serialized
    assert "Synthetic JD requiring Python and FastAPI." not in serialized

    run_count = db_session.query(AgentRun).count()
    assert run_count == 1
