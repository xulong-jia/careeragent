import pytest

from app.core.errors import AppError
from app.models.agent import AgentRun
from app.models.job import JobDescription, JobProfile
from app.models.project import Project
from app.models.rag import RagAnswerRun
from app.models.resume import Resume, ResumeVersion
from app.schemas.rag import RagSearchResult, RagSearchSource
from app.services import agent_service
from app.agents import state


PRIVATE_TEXT_KEYS = {"raw_text", "jd_raw_text", "chunk_text"}


def _create_resume_with_version(db_session, *, resume_id="resume_agent_0001"):
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


def _create_job_with_profile(db_session, *, jd_id="jd_agent_0001"):
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


def _create_project(db_session, version, *, project_id="project_agent_0001"):
    project = Project(
        id=project_id,
        resume_version_id=version.id,
        name="Synthetic API Project",
        role="Backend engineer",
        period="2026",
        background="Synthetic learning project for Python API workflow.",
        tech_stack=["Python", "FastAPI"],
        responsibilities=["Built FastAPI APIs with validation and tests."],
        results=["Improved local workflow quality with reproducible pytest checks."],
        evidence=[{"type": "test", "summary": "pytest smoke output exists"}],
        status="active",
    )
    db_session.add(project)
    db_session.commit()
    return project


def _assert_refs_are_private_safe(value):
    if isinstance(value, dict):
        assert PRIVATE_TEXT_KEYS.isdisjoint(value.keys())
        for child in value.values():
            _assert_refs_are_private_safe(child)
    elif isinstance(value, list):
        for child in value:
            _assert_refs_are_private_safe(child)


def test_unsupported_workflow_raises_safe_error(db_session):
    with pytest.raises(AppError) as exc_info:
        agent_service.create_run_for_workflow(
            db_session,
            {"workflow_name": "unsupported_workflow"},
        )

    assert exc_info.value.code == state.ERROR_AGENT_WORKFLOW_NOT_SUPPORTED
    assert db_session.query(AgentRun).count() == 0


def test_missing_resume_and_jd_returns_need_more_info(db_session):
    run = agent_service.create_run_for_workflow(
        db_session,
        {"workflow_name": state.WORKFLOW_JOB_APPLICATION_PREPARATION},
    )

    assert run.status == state.RUN_STATUS_NEED_MORE_INFO
    assert {slot["name"] for slot in run.missing_slots or []} == {
        "resume_version_id",
        "jd_id",
    }

    persisted = db_session.get(AgentRun, run.id)
    assert persisted is not None
    assert persisted.status == state.RUN_STATUS_NEED_MORE_INFO
    assert len(persisted.steps) == 1
    assert persisted.steps[0].step_name == "validate_inputs"
    assert persisted.steps[0].status == state.STEP_STATUS_NEED_MORE_INFO
    assert persisted.questions


def test_use_rag_without_query_returns_need_more_info(db_session):
    _, version = _create_resume_with_version(db_session)
    _create_job_with_profile(db_session)
    _create_project(db_session, version)

    run = agent_service.create_run_for_workflow(
        db_session,
        {
            "workflow_name": state.WORKFLOW_JOB_APPLICATION_PREPARATION,
            "resume_version_id": version.id,
            "jd_id": "jd_agent_0001",
            "use_rag": True,
        },
    )

    assert run.status == state.RUN_STATUS_NEED_MORE_INFO
    assert {slot["name"] for slot in run.missing_slots or []} == {"rag_query"}


def test_successful_workflow_creates_ordered_steps_and_skips_rag(db_session):
    _, version = _create_resume_with_version(db_session)
    _create_job_with_profile(db_session)
    _create_project(db_session, version)

    run = agent_service.create_run_for_workflow(
        db_session,
        {
            "workflow_name": state.WORKFLOW_JOB_APPLICATION_PREPARATION,
            "resume_version_id": version.id,
            "jd_id": "jd_agent_0001",
            "use_rag": False,
        },
    )

    persisted = db_session.get(AgentRun, run.id)
    assert persisted is not None
    assert persisted.status == state.RUN_STATUS_COMPLETED
    assert persisted.output_refs["resume_version_id"] == version.id
    assert persisted.output_refs["jd_id"] == "jd_agent_0001"
    assert persisted.output_refs["match_report_id"].startswith("match_")
    assert len(persisted.output_refs["project_rewrite_ids"]) == 1
    assert persisted.output_refs["interview_question_ids"]
    assert persisted.output_refs["study_plan_id"].startswith("study_plan_")
    assert persisted.output_refs["application_id"].startswith("app_")
    assert persisted.output_refs["rag_source_count"] == 0
    assert persisted.output_refs["grounded_source_count"] == 0
    assert persisted.output_refs["rag_context_warnings"] == ["RAG context was not requested."]
    assert persisted.output_refs["final_summary"]["total_score"] > 0
    assert persisted.output_refs["final_summary"]["rag_context"] == {
        "has_grounded_context": False,
        "source_count": 0,
        "grounded_source_count": 0,
        "warnings": ["RAG context was not requested."],
    }
    assert persisted.output_refs["final_summary"]["created_records"]

    step_names = [step.step_name for step in persisted.steps]
    assert step_names == [
        "validate_inputs",
        "load_resume_version",
        "load_job_profile",
        "run_match_report",
        "rag_search",
        "summarize_rag_context",
        "run_project_rewrites",
        "generate_interview_questions",
        "generate_study_plan",
        "create_or_link_application",
        "build_final_summary",
    ]
    assert [step.step_order for step in persisted.steps] == list(range(1, 12))
    assert [step.status for step in persisted.steps] == [
        state.STEP_STATUS_COMPLETED,
        state.STEP_STATUS_COMPLETED,
        state.STEP_STATUS_COMPLETED,
        state.STEP_STATUS_COMPLETED,
        state.STEP_STATUS_SKIPPED,
        state.STEP_STATUS_COMPLETED,
        state.STEP_STATUS_COMPLETED,
        state.STEP_STATUS_COMPLETED,
        state.STEP_STATUS_COMPLETED,
        state.STEP_STATUS_COMPLETED,
        state.STEP_STATUS_COMPLETED,
    ]
    summarize_step = [
        step for step in persisted.steps if step.step_name == "summarize_rag_context"
    ][0]
    assert summarize_step.output_refs["rag_answer_run_ids"] == []
    assert summarize_step.output_refs["rag_source_count"] == 0
    assert summarize_step.output_refs["grounded_source_count"] == 0
    assert summarize_step.output_refs["usable_rag_refs"] == []
    assert summarize_step.output_refs["rag_context_summary"] == {
        "has_grounded_context": False,
        "source_titles": [],
        "warnings": ["RAG context was not requested."],
    }

    for step in persisted.steps:
        _assert_refs_are_private_safe(step.input_refs)
        _assert_refs_are_private_safe(step.output_refs)


def test_workflow_completes_rag_search_with_source_refs(db_session, monkeypatch):
    _, version = _create_resume_with_version(db_session)
    _create_job_with_profile(db_session)

    def fake_search_documents(db, payload):
        return RagSearchResult(
            query=payload.query,
            top_k=payload.top_k,
            sources=[
                RagSearchSource(
                    doc_id="rag_doc_0001",
                    chunk_id="rag_chunk_0001",
                    title="Synthetic RAG note",
                    source_type="manual",
                    section="Overview",
                    snippet="This snippet should not be persisted in agent output refs.",
                    score=1.0,
                    metadata={"topic": "synthetic"},
                )
            ],
        )

    monkeypatch.setattr("app.agents.steps.rag_service.search_documents", fake_search_documents)

    run = agent_service.create_run_for_workflow(
        db_session,
        {
            "workflow_name": state.WORKFLOW_JOB_APPLICATION_PREPARATION,
            "resume_version_id": version.id,
            "jd_id": "jd_agent_0001",
            "use_rag": True,
            "rag_query": "synthetic evidence",
        },
    )

    persisted = db_session.get(AgentRun, run.id)
    rag_step = [step for step in persisted.steps if step.step_name == "rag_search"][0]
    summarize_step = [
        step for step in persisted.steps if step.step_name == "summarize_rag_context"
    ][0]

    assert persisted.status == state.RUN_STATUS_COMPLETED
    assert rag_step.status == state.STEP_STATUS_COMPLETED
    assert rag_step.output_refs["source_count"] == 1
    assert rag_step.output_refs["doc_ids"] == ["rag_doc_0001"]
    assert rag_step.output_refs["chunk_ids"] == ["rag_chunk_0001"]
    assert "snippet" not in rag_step.output_refs
    assert summarize_step.status == state.STEP_STATUS_COMPLETED
    assert summarize_step.output_refs["rag_source_count"] == 1
    assert summarize_step.output_refs["grounded_source_count"] == 1
    assert summarize_step.output_refs["usable_rag_refs"] == [
        {
            "source_type": "rag_search",
            "document_id": "rag_doc_0001",
            "chunk_id": "rag_chunk_0001",
            "title": "Synthetic RAG note",
        }
    ]
    assert summarize_step.output_refs["rag_context_summary"] == {
        "has_grounded_context": True,
        "source_titles": ["Synthetic RAG note"],
        "warnings": [],
    }
    assert "snippet" not in summarize_step.output_refs
    assert "This snippet should not be persisted" not in str(persisted.output_refs)
    assert persisted.output_refs["rag_source_count"] == 1
    assert persisted.output_refs["grounded_source_count"] == 1
    assert persisted.output_refs["final_summary"]["rag_context"] == {
        "has_grounded_context": True,
        "source_count": 1,
        "grounded_source_count": 1,
        "warnings": [],
    }


def test_workflow_summarizes_grounded_rag_answer_run_refs(db_session):
    _, version = _create_resume_with_version(db_session)
    _create_job_with_profile(db_session)
    answer_run = RagAnswerRun(
        id="rag_answer_run_agent_0001",
        question="What evidence supports Python API ownership?",
        filters_json={},
        top_k=1,
        retrieval_mode="deterministic_lexical",
        answer="Grounded deterministic answer.",
        answer_type="deterministic_summary",
        grounded=True,
        uncertainty="grounded",
        evidence_summary=["Grounded evidence summary."],
        citations_json=[],
        source_refs_json=[],
        retrieval_debug_json={
            "retrieval_mode": "deterministic_lexical",
            "candidate_count": 1,
            "top_k": 1,
        },
    )
    db_session.add(answer_run)
    db_session.commit()

    run = agent_service.create_run_for_workflow(
        db_session,
        {
            "workflow_name": state.WORKFLOW_JOB_APPLICATION_PREPARATION,
            "resume_version_id": version.id,
            "jd_id": "jd_agent_0001",
            "use_rag": False,
            "rag_answer_run_ids": [answer_run.id],
        },
    )

    persisted = db_session.get(AgentRun, run.id)
    summarize_step = [
        step for step in persisted.steps if step.step_name == "summarize_rag_context"
    ][0]

    assert persisted.status == state.RUN_STATUS_COMPLETED
    assert summarize_step.status == state.STEP_STATUS_COMPLETED
    assert summarize_step.output_refs["rag_source_count"] == 0
    assert summarize_step.output_refs["grounded_source_count"] == 1
    assert summarize_step.output_refs["usable_rag_refs"] == [
        {"source_type": "rag_answer_run", "source_id": answer_run.id}
    ]
    assert summarize_step.output_refs["rag_context_summary"] == {
        "has_grounded_context": True,
        "source_titles": [],
        "warnings": [],
    }
    assert persisted.output_refs["final_summary"]["rag_context"] == {
        "has_grounded_context": True,
        "source_count": 0,
        "grounded_source_count": 1,
        "warnings": [],
    }


def test_failed_step_records_error_and_marks_run_failed(db_session, monkeypatch):
    _, version = _create_resume_with_version(db_session)
    _create_job_with_profile(db_session)

    def fail_match_report(db, payload):
        raise RuntimeError("synthetic match failure without private text")

    monkeypatch.setattr("app.agents.steps.match_service.run_match_report", fail_match_report)

    run = agent_service.create_run_for_workflow(
        db_session,
        {
            "workflow_name": state.WORKFLOW_JOB_APPLICATION_PREPARATION,
            "resume_version_id": version.id,
            "jd_id": "jd_agent_0001",
            "use_rag": False,
        },
    )

    persisted = db_session.get(AgentRun, run.id)
    failed_steps = [step for step in persisted.steps if step.status == state.STEP_STATUS_FAILED]

    assert run.status == state.RUN_STATUS_FAILED
    assert persisted.status == state.RUN_STATUS_FAILED
    assert len(failed_steps) == 1
    assert failed_steps[0].step_name == "run_match_report"
    assert failed_steps[0].error_code == state.ERROR_MATCH_REPORT_FAILED
    assert persisted.error_code == state.ERROR_MATCH_REPORT_FAILED
    assert "raw_text" not in (persisted.error_message or "")
