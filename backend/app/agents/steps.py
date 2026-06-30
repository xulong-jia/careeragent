from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import state
from app.core.errors import AppError
from app.models.application import Application
from app.models.job import JobDescription, JobProfile
from app.models.project import Project
from app.models.resume import Resume, ResumeVersion
from app.schemas.applications import ApplicationCreateRequest, ApplicationUpdateRequest
from app.schemas.interviews import InterviewQuestionGenerateRequest
from app.schemas.matches import MatchRunRequest
from app.schemas.projects import ProjectRewriteRequest
from app.schemas.rag import RagSearchFilters, RagSearchRequest
from app.schemas.study_plans import StudyPlanGenerateRequest
from app.services import (
    application_service,
    interview_service,
    match_service,
    project_rewrite_service,
    rag_service,
    study_plan_service,
)


@dataclass
class WorkflowContext:
    payload: dict[str, object]
    resolved: dict[str, object] = field(default_factory=dict)


@dataclass
class StepResult:
    status: str
    output_refs: dict[str, object] = field(default_factory=dict)
    missing_slots: list[dict[str, object]] = field(default_factory=list)
    questions: list[dict[str, object]] = field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None


def initial_input_refs(payload: dict[str, object]) -> dict[str, object]:
    return {
        "resume_id": payload.get("resume_id"),
        "resume_version_id": payload.get("resume_version_id"),
        "jd_id": payload.get("jd_id"),
        "project_ids": _normalize_id_list(payload.get("project_ids")),
        "application_id": payload.get("application_id"),
        "create_application": bool(payload.get("create_application", True)),
        "use_rag": bool(payload.get("use_rag", False)),
        "rag_query_present": bool(str(payload.get("rag_query") or "").strip()),
        "rag_answer_run_ids": _normalize_id_list(payload.get("rag_answer_run_ids")),
    }


def _missing_slot(name: str, reason: str, question: str) -> tuple[dict[str, str], dict[str, str]]:
    return {"name": name, "reason": reason}, {"slot": name, "question": question}


def _normalize_id_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        text = str(item).strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def _latest_active_resume_version(db: Session, resume_id: str) -> ResumeVersion | None:
    return db.scalars(
        select(ResumeVersion)
        .where(ResumeVersion.resume_id == resume_id)
        .where(ResumeVersion.status == "active")
        .order_by(ResumeVersion.version_number.desc(), ResumeVersion.created_at.desc())
        .limit(1)
    ).first()


def _latest_job_profile(db: Session, jd_id: str) -> JobProfile | None:
    return db.scalars(
        select(JobProfile)
        .where(JobProfile.jd_id == jd_id)
        .order_by(JobProfile.profile_version.desc(), JobProfile.created_at.desc())
        .limit(1)
    ).first()


def validate_inputs(db: Session, context: WorkflowContext) -> StepResult:
    payload = context.payload
    resume_id = str(payload.get("resume_id") or "").strip() or None
    resume_version_id = str(payload.get("resume_version_id") or "").strip() or None
    jd_id = str(payload.get("jd_id") or "").strip() or None
    project_ids = _normalize_id_list(payload.get("project_ids"))
    application_id = str(payload.get("application_id") or "").strip() or None
    create_application = bool(payload.get("create_application", True))
    rag_answer_run_ids = _normalize_id_list(payload.get("rag_answer_run_ids"))
    use_rag = bool(payload.get("use_rag", False))
    rag_query = str(payload.get("rag_query") or "").strip()

    missing_slots: list[dict[str, str]] = []
    questions: list[dict[str, str]] = []

    if not resume_id and not resume_version_id:
        slot, question = _missing_slot(
            "resume_version_id",
            "Either resume_id or resume_version_id is required.",
            "请选择一份 Resume 或 Resume Version 后再运行 workflow。",
        )
        missing_slots.append(slot)
        questions.append(question)

    if not jd_id:
        slot, question = _missing_slot(
            "jd_id",
            "A job description is required.",
            "请选择一个 JD 后再运行 workflow。",
        )
        missing_slots.append(slot)
        questions.append(question)

    if use_rag and not rag_query:
        slot, question = _missing_slot(
            "rag_query",
            "rag_query is required when use_rag is true.",
            "请输入 RAG 检索问题，或关闭 use_rag。",
        )
        missing_slots.append(slot)
        questions.append(question)

    resume_version: ResumeVersion | None = None
    if resume_version_id:
        resume_version = db.get(ResumeVersion, resume_version_id)
        if not resume_version:
            slot, question = _missing_slot(
                "resume_version_id",
                "Resume version was not found.",
                "请选择一个存在的 Resume Version。",
            )
            missing_slots.append(slot)
            questions.append(question)
    elif resume_id:
        resume = db.get(Resume, resume_id)
        if not resume or resume.status != "active":
            slot, question = _missing_slot(
                "resume_id",
                "Resume was not found.",
                "请选择一个存在的 Resume。",
            )
            missing_slots.append(slot)
            questions.append(question)
        else:
            resume_version = _latest_active_resume_version(db, resume_id)
            if not resume_version:
                slot, question = _missing_slot(
                    "resume_version_id",
                    "Active resume version was not found.",
                    "请先创建或选择一个 active Resume Version。",
                )
                missing_slots.append(slot)
                questions.append(question)

    job_profile: JobProfile | None = None
    if jd_id:
        job = db.get(JobDescription, jd_id)
        if not job or job.status != "active":
            slot, question = _missing_slot(
                "jd_id",
                "JD was not found.",
                "请选择一个存在的 JD。",
            )
            missing_slots.append(slot)
            questions.append(question)
        else:
            job_profile = _latest_job_profile(db, jd_id)
            if not job_profile:
                slot, question = _missing_slot(
                    "jd_id",
                    "JD profile was not found.",
                    "请先创建可用的 JD profile。",
                )
                missing_slots.append(slot)
                questions.append(question)

    for project_id in project_ids:
        project = db.get(Project, project_id)
        if not project or project.status != "active":
            slot, question = _missing_slot(
                "project_ids",
                f"Project {project_id} was not found.",
                "请选择存在且 active 的 Project，或清空 project_ids 让 workflow 自动发现。",
            )
            missing_slots.append(slot)
            questions.append(question)

    if application_id and not db.get(Application, application_id):
        slot, question = _missing_slot(
            "application_id",
            "Application was not found.",
            "请选择存在的 Application，或清空 application_id 让 workflow 创建 draft。",
        )
        missing_slots.append(slot)
        questions.append(question)

    if missing_slots:
        return StepResult(
            status=state.STEP_STATUS_NEED_MORE_INFO,
            output_refs={
                "missing_slot_count": len(missing_slots),
                "rag_query_present": bool(rag_query),
            },
            missing_slots=missing_slots,
            questions=questions,
        )

    assert resume_version is not None
    assert jd_id is not None
    assert job_profile is not None
    context.resolved.update(
        {
            "resume_id": resume_version.resume_id,
            "resume_version_id": resume_version.id,
            "jd_id": jd_id,
            "job_profile_id": job_profile.id,
            "project_ids": project_ids,
            "application_id": application_id,
            "create_application": create_application,
            "use_rag": use_rag,
            "rag_query": rag_query,
            "rag_answer_run_ids": rag_answer_run_ids,
        }
    )
    return StepResult(
        status=state.STEP_STATUS_COMPLETED,
        output_refs={
            "resume_id": resume_version.resume_id,
            "resume_version_id": resume_version.id,
            "jd_id": jd_id,
            "job_profile_id": job_profile.id,
            "project_ids": project_ids,
            "application_id": application_id,
            "create_application": create_application,
            "use_rag": use_rag,
            "rag_query_present": bool(rag_query),
            "rag_answer_run_ids": rag_answer_run_ids,
        },
    )


def load_resume_version(db: Session, context: WorkflowContext) -> StepResult:
    resume_version_id = str(context.resolved["resume_version_id"])
    version = db.get(ResumeVersion, resume_version_id)
    if not version:
        raise AppError(
            code=state.ERROR_RESUME_VERSION_NOT_FOUND,
            message="Resume version was not found.",
            status_code=404,
            details={"resume_version_id": resume_version_id},
        )
    context.resolved["resume_id"] = version.resume_id
    return StepResult(
        status=state.STEP_STATUS_COMPLETED,
        output_refs={
            "resume_id": version.resume_id,
            "resume_version_id": version.id,
            "version_number": version.version_number,
            "status": version.status,
        },
    )


def load_job_profile(db: Session, context: WorkflowContext) -> StepResult:
    jd_id = str(context.resolved["jd_id"])
    job = db.get(JobDescription, jd_id)
    if not job or job.status != "active":
        raise AppError(
            code=state.ERROR_JOB_NOT_FOUND,
            message="JD was not found.",
            status_code=404,
            details={"jd_id": jd_id},
        )
    profile = _latest_job_profile(db, jd_id)
    if not profile:
        raise AppError(
            code=state.ERROR_JOB_NOT_FOUND,
            message="JD profile was not found.",
            status_code=404,
            details={"jd_id": jd_id},
        )
    context.resolved["job_profile_id"] = profile.id
    context.resolved["company"] = job.company
    context.resolved["job_title"] = job.job_title
    context.resolved["role_category"] = profile.role_category
    return StepResult(
        status=state.STEP_STATUS_COMPLETED,
        output_refs={
            "jd_id": jd_id,
            "job_profile_id": profile.id,
            "company": job.company,
            "job_title": job.job_title,
            "role_category": profile.role_category,
        },
    )


def run_match_report(db: Session, context: WorkflowContext) -> StepResult:
    try:
        report = match_service.run_match_report(
            db,
            MatchRunRequest(
                resume_id=str(context.resolved["resume_id"]),
                resume_version_id=str(context.resolved["resume_version_id"]),
                jd_id=str(context.resolved["jd_id"]),
            ),
        )
    except Exception as exc:
        raise AppError(
            code=state.ERROR_MATCH_REPORT_FAILED,
            message="Match report step failed.",
            status_code=500,
        ) from exc

    context.resolved["match_report_id"] = report.match_report_id
    context.resolved["match_total_score"] = report.total_score
    context.resolved["match_strengths"] = list(report.strengths)
    context.resolved["match_gaps"] = list(report.gaps)
    return StepResult(
        status=state.STEP_STATUS_COMPLETED,
        output_refs={
            "match_report_id": report.match_report_id,
            "resume_version_id": report.resume_version_id,
            "jd_id": report.jd_id,
            "total_score": report.total_score,
            "top_strengths": list(report.strengths)[:3],
            "top_gaps": list(report.gaps)[:3],
            "risk_flag_count": len(report.risk_flags),
        },
    )


def rag_search(db: Session, context: WorkflowContext) -> StepResult:
    if not bool(context.resolved.get("use_rag", False)):
        context.resolved["rag_source_count"] = 0
        return StepResult(
            status=state.STEP_STATUS_SKIPPED,
            output_refs={"reason": "use_rag is false", "source_count": 0},
        )

    rag_query = str(context.resolved.get("rag_query") or "")
    try:
        result = rag_service.search_documents(
            db,
            RagSearchRequest(
                query=rag_query,
                top_k=5,
                filters=RagSearchFilters(),
            ),
        )
    except Exception as exc:
        raise AppError(
            code=state.ERROR_RAG_SEARCH_FAILED,
            message="RAG search step failed.",
            status_code=500,
        ) from exc

    sources = result.sources
    context.resolved["rag_source_count"] = len(sources)
    context.resolved["rag_doc_ids"] = [source.doc_id for source in sources]
    context.resolved["rag_chunk_ids"] = [source.chunk_id for source in sources]
    return StepResult(
        status=state.STEP_STATUS_COMPLETED,
        output_refs={
            "source_count": len(sources),
            "doc_ids": [source.doc_id for source in sources],
            "chunk_ids": [source.chunk_id for source in sources],
            "scores": [source.score for source in sources],
            "uncertainty": result.uncertainty,
        },
    )


def _projects_for_workflow(db: Session, context: WorkflowContext) -> list[Project]:
    project_ids = list(context.resolved.get("project_ids") or [])
    if project_ids:
        projects: list[Project] = []
        for project_id in project_ids:
            project = db.get(Project, str(project_id))
            if project and project.status == "active":
                projects.append(project)
        return projects

    resume_version_id = str(context.resolved["resume_version_id"])
    return list(
        db.scalars(
            select(Project)
            .where(Project.resume_version_id == resume_version_id)
            .where(Project.status == "active")
            .order_by(Project.created_at, Project.id)
        ).all()
    )


def run_project_rewrites(db: Session, context: WorkflowContext) -> StepResult:
    projects = _projects_for_workflow(db, context)
    if not projects:
        context.resolved["project_ids"] = []
        context.resolved["project_rewrite_ids"] = []
        return StepResult(
            status=state.STEP_STATUS_SKIPPED,
            output_refs={
                "reason": "no_active_project_for_resume_version",
                "project_ids": [],
                "project_rewrite_ids": [],
            },
        )

    rewrite_ids: list[str] = []
    for project in projects:
        rewrite = project_rewrite_service.create_project_rewrite(
            db,
            project.id,
            ProjectRewriteRequest(
                jd_id=str(context.resolved["jd_id"]),
                resume_version_id=str(context.resolved["resume_version_id"]),
                match_report_id=str(context.resolved["match_report_id"]),
            ),
        )
        rewrite_ids.append(rewrite.id)

    project_ids = [project.id for project in projects]
    context.resolved["project_ids"] = project_ids
    context.resolved["project_rewrite_ids"] = rewrite_ids
    return StepResult(
        status=state.STEP_STATUS_COMPLETED,
        output_refs={
            "project_ids": project_ids,
            "project_rewrite_ids": rewrite_ids,
            "rewrite_count": len(rewrite_ids),
        },
    )


def generate_interview_questions(db: Session, context: WorkflowContext) -> StepResult:
    project_ids = list(context.resolved.get("project_ids") or [])
    rewrite_ids = list(context.resolved.get("project_rewrite_ids") or [])
    rag_answer_run_ids = list(context.resolved.get("rag_answer_run_ids") or [])
    response = interview_service.generate_questions(
        db,
        InterviewQuestionGenerateRequest(
            jd_id=str(context.resolved["jd_id"]),
            resume_version_id=str(context.resolved["resume_version_id"]),
            project_id=str(project_ids[0]) if project_ids else None,
            project_rewrite_id=str(rewrite_ids[0]) if rewrite_ids else None,
            max_questions=6,
            rag_answer_run_ids=[str(value) for value in rag_answer_run_ids],
        ),
    )
    question_ids = [question.id for question in response.questions]
    context.resolved["interview_question_ids"] = question_ids
    return StepResult(
        status=state.STEP_STATUS_COMPLETED,
        output_refs={
            "interview_question_ids": question_ids,
            "question_count": len(question_ids),
            "warnings": response.warnings,
            "need_more_info": response.need_more_info,
        },
    )


def generate_study_plan(db: Session, context: WorkflowContext) -> StepResult:
    rewrite_ids = list(context.resolved.get("project_rewrite_ids") or [])
    rag_answer_run_ids = list(context.resolved.get("rag_answer_run_ids") or [])
    plan = study_plan_service.generate_study_plan(
        db,
        StudyPlanGenerateRequest(
            target_role=str(context.resolved.get("role_category") or "Target Role"),
            match_report_id=str(context.resolved["match_report_id"]),
            project_rewrite_id=str(rewrite_ids[0]) if rewrite_ids else None,
            rag_answer_run_ids=[str(value) for value in rag_answer_run_ids],
        ),
    )
    context.resolved["study_plan_id"] = plan.id
    return StepResult(
        status=state.STEP_STATUS_COMPLETED,
        output_refs={
            "study_plan_id": plan.id,
            "target_role": plan.target_role,
            "phase_count": len(plan.phases),
        },
    )


def create_or_link_application(db: Session, context: WorkflowContext) -> StepResult:
    required_refs = [
        "jd_id",
        "resume_version_id",
        "match_report_id",
        "agent_run_id",
    ]
    missing_refs = [name for name in required_refs if not context.resolved.get(name)]
    if missing_refs:
        missing_slots = [
            {
                "name": "application_refs",
                "reason": "Application linkage requires jd_id, resume_version_id, match_report_id, and agent_run_id.",
            }
        ]
        questions = [
            {
                "slot": "application_refs",
                "question": "请先完成 JD、Resume Version、Match Report 和 Agent Run 后再绑定 Application。",
            }
        ]
        return StepResult(
            status=state.STEP_STATUS_NEED_MORE_INFO,
            output_refs={"missing_refs": missing_refs},
            missing_slots=missing_slots,
            questions=questions,
        )

    application_id = str(context.resolved.get("application_id") or "").strip()
    if application_id:
        application = application_service.update_application(
            db,
            application_id,
            ApplicationUpdateRequest(
                jd_id=str(context.resolved["jd_id"]),
                resume_version_id=str(context.resolved["resume_version_id"]),
                match_report_id=str(context.resolved["match_report_id"]),
                agent_run_id=str(context.resolved["agent_run_id"]),
            ),
        )
        mode = "linked_existing"
    elif not bool(context.resolved.get("create_application", True)):
        context.resolved["application_id"] = None
        return StepResult(
            status=state.STEP_STATUS_SKIPPED,
            output_refs={"reason": "create_application is false"},
        )
    else:
        application = application_service.create_application(
            db,
            ApplicationCreateRequest(
                company=str(context.resolved.get("company") or "Unknown Company"),
                role_title=str(context.resolved.get("job_title") or "Target Role"),
                role_category=str(context.resolved.get("role_category") or "") or None,
                jd_id=str(context.resolved["jd_id"]),
                resume_version_id=str(context.resolved["resume_version_id"]),
                match_report_id=str(context.resolved["match_report_id"]),
                agent_run_id=str(context.resolved["agent_run_id"]),
                status="saved",
                reflection="Created by deterministic Agent Workflow.",
                tags=["agent_workflow"],
            ),
        )
        mode = "created_draft"

    context.resolved["application_id"] = application.application_id
    return StepResult(
        status=state.STEP_STATUS_COMPLETED,
        output_refs={
            "application_id": application.application_id,
            "agent_run_id": application.agent_run_id,
            "status": application.status,
            "mode": mode,
        },
    )


def build_final_summary(db: Session, context: WorkflowContext) -> StepResult:
    resume_version_id = str(context.resolved["resume_version_id"])
    jd_id = str(context.resolved["jd_id"])
    match_report_id = str(context.resolved["match_report_id"])
    rag_source_count = int(context.resolved.get("rag_source_count") or 0)
    project_rewrite_ids = list(context.resolved.get("project_rewrite_ids") or [])
    interview_question_ids = list(context.resolved.get("interview_question_ids") or [])
    study_plan_id = context.resolved.get("study_plan_id")
    application_id = context.resolved.get("application_id")
    final_summary = {
        "total_score": int(context.resolved.get("match_total_score") or 0),
        "top_strengths": list(context.resolved.get("match_strengths") or [])[:3],
        "top_gaps": list(context.resolved.get("match_gaps") or [])[:3],
        "next_actions": [
            "Review generated project rewrite suggestions.",
            "Use generated interview questions for targeted practice.",
            "Follow the study plan tasks before changing resume claims.",
            "Update the linked application status manually when progress changes.",
        ],
        "created_records": [
            {"type": "match_report", "id": match_report_id},
            *[
                {"type": "project_rewrite", "id": rewrite_id}
                for rewrite_id in project_rewrite_ids
            ],
            *[
                {"type": "interview_question", "id": question_id}
                for question_id in interview_question_ids
            ],
            *([{"type": "study_plan", "id": study_plan_id}] if study_plan_id else []),
            *([{"type": "application", "id": application_id}] if application_id else []),
        ],
    }
    return StepResult(
        status=state.STEP_STATUS_COMPLETED,
        output_refs={
            "resume_version_id": resume_version_id,
            "jd_id": jd_id,
            "match_report_id": match_report_id,
            "project_rewrite_ids": project_rewrite_ids,
            "interview_question_ids": interview_question_ids,
            "study_plan_id": study_plan_id,
            "application_id": application_id,
            "rag_answer_run_ids": list(context.resolved.get("rag_answer_run_ids") or []),
            "rag_source_count": rag_source_count,
            "final_summary": final_summary,
        },
    )


STEP_EXECUTORS = {
    "validate_inputs": validate_inputs,
    "load_resume_version": load_resume_version,
    "load_job_profile": load_job_profile,
    "run_match_report": run_match_report,
    "rag_search": rag_search,
    "run_project_rewrites": run_project_rewrites,
    "generate_interview_questions": generate_interview_questions,
    "generate_study_plan": generate_study_plan,
    "create_or_link_application": create_or_link_application,
    "build_final_summary": build_final_summary,
}
