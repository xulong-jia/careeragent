from sqlalchemy.orm import Session

from app.agents import state
from app.agents.steps import STEP_EXECUTORS, WorkflowContext, initial_input_refs
from app.agents.workflows import WorkflowDefinition
from app.core.errors import AppError
from app.core.versioning import version_metadata
from app.models.agent import AgentRun
from app.repositories import agent_repository
from app.schemas.evaluations import BadCaseCreateRequest
from app.services import evaluation_service


PRIVATE_REF_KEYS = {
    "raw_text",
    "jd_raw_text",
    "chunk_text",
    "full_text",
    "resume_text",
    "job_text",
    "snippet",
    "api_key",
    "secret",
    "token",
}
CONTENT_REF_KEYS = {"rag_query"}


def _safe_error_message(exc: Exception) -> str:
    if isinstance(exc, AppError):
        return exc.message
    return "Agent workflow step failed."


def _safe_refs(value: object) -> object:
    if isinstance(value, dict):
        safe: dict[str, object] = {}
        for key, child in value.items():
            normalized = str(key).lower()
            if normalized in CONTENT_REF_KEYS:
                safe[str(key) + "_present"] = bool(str(child or "").strip())
                continue
            if any(pattern in normalized for pattern in PRIVATE_REF_KEYS):
                continue
            safe[str(key)] = _safe_refs(child)
        return safe
    if isinstance(value, list):
        return [_safe_refs(item) for item in value]
    if isinstance(value, str) and len(value) > 160:
        return f"{value[:157]}..."
    return value


def _workflow_run_config(
    workflow: WorkflowDefinition,
    *,
    payload: dict[str, object],
    attempt: int,
) -> dict[str, object]:
    metadata = version_metadata()
    return {
        "workflow_name": workflow.name,
        "workflow_version": "agent-workflow-productionization-v2.5",
        "attempt": attempt,
        "execution_mode": "sync_local_service_pipeline",
        "required_slots": list(workflow.required_slots),
        "steps": list(workflow.steps),
        "step_count": len(workflow.steps),
        "use_rag": bool(payload.get("use_rag", False)),
        "rag_mode": "service_search" if payload.get("use_rag", False) else "none",
        "model_version": metadata.get("model_version"),
        "schema_version": metadata.get("schema_version"),
        "code_version": metadata.get("code_version"),
    }


def _bad_case_payload(
    *,
    run: AgentRun,
    step_id: str,
    step_name: str,
    attempt: int,
    error_code: str,
    error_message: str,
) -> dict[str, object]:
    return {
        "suggested_bad_case_type": "agent_step_failed",
        "source_type": "agent_step",
        "source_id": step_id,
        "run_id": run.id,
        "workflow_name": run.workflow_name,
        "failed_step": step_name,
        "attempt": attempt,
        "error_code": error_code,
        "error_message": error_message,
        "privacy_note": "Payload contains refs and short metadata only; raw Resume/JD/RAG text is excluded.",
    }


def _create_bad_case_draft(
    db: Session,
    *,
    run: AgentRun,
    step_id: str,
    step_name: str,
    attempt: int,
    error_code: str,
    error_message: str,
) -> tuple[str | None, dict[str, object]]:
    payload = _bad_case_payload(
        run=run,
        step_id=step_id,
        step_name=step_name,
        attempt=attempt,
        error_code=error_code,
        error_message=error_message,
    )
    try:
        bad_case = evaluation_service.create_bad_case(
            db,
            BadCaseCreateRequest(
                source_type="agent_step",
                source_id=step_id,
                category="agent_step_failed",
                severity="medium",
                title=f"Agent step failed: {step_name}",
                description=(
                    f"Workflow {run.workflow_name} failed at step {step_name} "
                    f"on attempt {attempt}."
                ),
                expected_behavior="Agent workflow should either complete or request missing information.",
                actual_behavior=f"{error_code}: {error_message}",
                suggested_fix="Review the failed step inputs, service dependency, and retry policy.",
                root_cause="Generated automatically from Agent workflow failure.",
                fix_strategy="Triage as a Bad Case regression before marking the workflow stable.",
                tags=["agent_workflow", run.workflow_name, step_name],
            ),
        )
    except Exception:
        return None, payload
    payload["bad_case_id"] = bad_case.id
    return bad_case.id, payload


def run_workflow(
    db: Session,
    *,
    workflow: WorkflowDefinition,
    payload: dict[str, object],
    existing_run: AgentRun | None = None,
    attempt: int = 1,
    start_status: str = state.RUN_STATUS_RUNNING,
) -> AgentRun:
    normalized_payload = {**payload, "workflow_name": workflow.name}
    input_refs = _safe_refs(initial_input_refs(normalized_payload))
    run_config = _workflow_run_config(
        workflow,
        payload=normalized_payload,
        attempt=attempt,
    )
    context = WorkflowContext(payload=normalized_payload, workflow_name=workflow.name)
    if existing_run:
        run = agent_repository.prepare_run_attempt(
            db,
            existing_run,
            input_refs=input_refs,
            run_config=run_config,
            attempt=attempt,
            status=start_status,
        )
    else:
        run = agent_repository.create_run(
            db,
            workflow_name=workflow.name,
            input_refs=input_refs,
            run_config=run_config,
        )
    context.resolved["agent_run_id"] = run.id
    agent_repository.update_run_status(db, run, status=state.RUN_STATUS_RUNNING)

    for step_order, step_name in enumerate(workflow.steps, start=1):
        executor = STEP_EXECUTORS[step_name]
        step_input_refs = (
            input_refs
            if step_name in {"validate_inputs", "validate_application_review_inputs"}
            else _safe_refs(dict(context.resolved))
        )
        step = agent_repository.create_step(
            db,
            run_id=run.id,
            step_name=step_name,
            step_order=step_order,
            attempt=attempt,
            input_refs=step_input_refs,
            run_config=run_config,
            privacy_safe_payload={
                "attempt": attempt,
                "step_name": step_name,
                "input_refs": step_input_refs,
            },
        )
        agent_repository.update_step_status(db, step, status=state.STEP_STATUS_RUNNING)

        try:
            result = executor(db, context)
        except Exception as exc:
            error_code = exc.code if isinstance(exc, AppError) else state.ERROR_AGENT_STEP_FAILED
            if step_name == "run_match_report":
                error_code = state.ERROR_MATCH_REPORT_FAILED
            elif step_name == "rag_search":
                error_code = state.ERROR_RAG_SEARCH_FAILED
            elif step_name == "run_project_rewrites":
                error_code = state.ERROR_PROJECT_REWRITE_FAILED
            elif step_name == "generate_interview_questions":
                error_code = state.ERROR_INTERVIEW_GENERATION_FAILED
            elif step_name == "generate_study_plan":
                error_code = state.ERROR_STUDY_PLAN_FAILED
            elif step_name == "create_or_link_application":
                error_code = state.ERROR_APPLICATION_LINK_FAILED
            error_message = _safe_error_message(exc)
            agent_repository.update_step_error(
                db,
                step,
                error_code=error_code,
                error_message=error_message,
            )
            agent_repository.update_run_error(
                db,
                run,
                error_code=error_code,
                error_message=error_message,
            )
            bad_case_id, bad_case_payload = _create_bad_case_draft(
                db,
                run=run,
                step_id=step.id,
                step_name=step_name,
                attempt=attempt,
                error_code=error_code,
                error_message=error_message,
            )
            agent_repository.update_run_bad_case(
                db,
                run,
                bad_case_id=bad_case_id,
                bad_case_payload=bad_case_payload,
            )
            return run

        output_refs = _safe_refs(result.output_refs)
        if result.status == state.STEP_STATUS_NEED_MORE_INFO:
            agent_repository.update_step_outputs(
                db,
                step,
                status=state.STEP_STATUS_NEED_MORE_INFO,
                output_refs=output_refs,
            )
            agent_repository.update_run_need_more_info(
                db,
                run,
                missing_slots=result.missing_slots,
                questions=result.questions,
                output_refs=output_refs,
            )
            return run

        agent_repository.update_step_outputs(
            db,
            step,
            status=result.status,
            output_refs=output_refs,
        )
        if step_name in {"build_final_summary", "build_application_review_summary"}:
            agent_repository.update_run_outputs(db, run, output_refs=output_refs)

    agent_repository.update_run_status(db, run, status=state.RUN_STATUS_COMPLETED)
    return run
