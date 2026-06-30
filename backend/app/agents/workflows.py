from dataclasses import dataclass

from app.agents import state


@dataclass(frozen=True)
class WorkflowDefinition:
    name: str
    description: str
    steps: tuple[str, ...]
    required_slots: tuple[str, ...]


JOB_APPLICATION_PREPARATION = WorkflowDefinition(
    name=state.WORKFLOW_JOB_APPLICATION_PREPARATION,
    description=(
        "Prepare a deterministic job application workflow using Resume, JD, "
        "Match, Project, Interview, Study Plan, Application, and optional RAG refs."
    ),
    steps=(
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
    ),
    required_slots=("jd_id",),
)

WORKFLOWS = {
    JOB_APPLICATION_PREPARATION.name: JOB_APPLICATION_PREPARATION,
}


def get_workflow_definition(workflow_name: str) -> WorkflowDefinition | None:
    return WORKFLOWS.get(workflow_name)
