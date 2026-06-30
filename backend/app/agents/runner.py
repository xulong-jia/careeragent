from sqlalchemy.orm import Session

from app.agents import state
from app.agents.steps import STEP_EXECUTORS, WorkflowContext, initial_input_refs
from app.agents.workflows import WorkflowDefinition
from app.core.errors import AppError
from app.models.agent import AgentRun
from app.repositories import agent_repository


def _safe_error_message(exc: Exception) -> str:
    if isinstance(exc, AppError):
        return exc.message
    return "Agent workflow step failed."


def run_workflow(
    db: Session,
    *,
    workflow: WorkflowDefinition,
    payload: dict[str, object],
) -> AgentRun:
    context = WorkflowContext(payload=payload)
    run = agent_repository.create_run(
        db,
        workflow_name=workflow.name,
        input_refs=initial_input_refs(payload),
    )
    context.resolved["agent_run_id"] = run.id
    agent_repository.update_run_status(db, run, status=state.RUN_STATUS_RUNNING)

    for step_order, step_name in enumerate(workflow.steps, start=1):
        executor = STEP_EXECUTORS[step_name]
        step = agent_repository.create_step(
            db,
            run_id=run.id,
            step_name=step_name,
            step_order=step_order,
            input_refs=dict(context.resolved) if step_name != "validate_inputs" else initial_input_refs(payload),
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
            return run

        if result.status == state.STEP_STATUS_NEED_MORE_INFO:
            agent_repository.update_step_outputs(
                db,
                step,
                status=state.STEP_STATUS_NEED_MORE_INFO,
                output_refs=result.output_refs,
            )
            agent_repository.update_run_need_more_info(
                db,
                run,
                missing_slots=result.missing_slots,
                questions=result.questions,
                output_refs=result.output_refs,
            )
            return run

        agent_repository.update_step_outputs(
            db,
            step,
            status=result.status,
            output_refs=result.output_refs,
        )
        if step_name == "build_final_summary":
            agent_repository.update_run_outputs(db, run, output_refs=result.output_refs)

    agent_repository.update_run_status(db, run, status=state.RUN_STATUS_COMPLETED)
    return run
