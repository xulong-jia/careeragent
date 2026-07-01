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

INTERVIEW_PREPARATION = WorkflowDefinition(
    name=state.WORKFLOW_INTERVIEW_PREPARATION,
    description=(
        "Prepare interview practice from Resume, JD, Match, optional RAG refs, "
        "and generated interview questions."
    ),
    steps=(
        "validate_inputs",
        "load_resume_version",
        "load_job_profile",
        "run_match_report",
        "rag_search",
        "summarize_rag_context",
        "generate_interview_questions",
        "build_final_summary",
    ),
    required_slots=("resume_version_id", "jd_id"),
)

APPLICATION_REVIEW = WorkflowDefinition(
    name=state.WORKFLOW_APPLICATION_REVIEW,
    description=(
        "Review an existing application tracking record and produce privacy-safe "
        "follow-up refs and risk flags."
    ),
    steps=(
        "validate_application_review_inputs",
        "load_application_context",
        "build_application_review_summary",
    ),
    required_slots=("application_id",),
)

STUDY_GAP_PLANNING = WorkflowDefinition(
    name=state.WORKFLOW_STUDY_GAP_PLANNING,
    description=(
        "Create a study gap plan from Resume, JD, Match, optional RAG refs, and "
        "Study Plan generation."
    ),
    steps=(
        "validate_inputs",
        "load_resume_version",
        "load_job_profile",
        "run_match_report",
        "rag_search",
        "summarize_rag_context",
        "generate_study_plan",
        "build_final_summary",
    ),
    required_slots=("resume_version_id", "jd_id"),
)

WORKFLOWS = {
    JOB_APPLICATION_PREPARATION.name: JOB_APPLICATION_PREPARATION,
    INTERVIEW_PREPARATION.name: INTERVIEW_PREPARATION,
    APPLICATION_REVIEW.name: APPLICATION_REVIEW,
    STUDY_GAP_PLANNING.name: STUDY_GAP_PLANNING,
}


def get_workflow_definition(workflow_name: str) -> WorkflowDefinition | None:
    return WORKFLOWS.get(workflow_name)
