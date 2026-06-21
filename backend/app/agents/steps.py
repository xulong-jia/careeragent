from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import state
from app.core.errors import AppError
from app.models.job import JobDescription, JobProfile
from app.models.resume import Resume, ResumeVersion
from app.schemas.matches import MatchRunRequest
from app.schemas.rag import RagSearchFilters, RagSearchRequest
from app.services import match_service, rag_service


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
        "use_rag": bool(payload.get("use_rag", False)),
        "rag_query_present": bool(str(payload.get("rag_query") or "").strip()),
    }


def _missing_slot(name: str, reason: str, question: str) -> tuple[dict[str, str], dict[str, str]]:
    return {"name": name, "reason": reason}, {"slot": name, "question": question}


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
    use_rag = bool(payload.get("use_rag", False))
    rag_query = str(payload.get("rag_query") or "").strip()

    missing_slots: list[dict[str, str]] = []
    questions: list[dict[str, str]] = []

    if not resume_id and not resume_version_id:
        slot, question = _missing_slot(
            "resume",
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
            "use_rag": use_rag,
            "rag_query": rag_query,
        }
    )
    return StepResult(
        status=state.STEP_STATUS_COMPLETED,
        output_refs={
            "resume_id": resume_version.resume_id,
            "resume_version_id": resume_version.id,
            "jd_id": jd_id,
            "job_profile_id": job_profile.id,
            "use_rag": use_rag,
            "rag_query_present": bool(rag_query),
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
    profile = _latest_job_profile(db, jd_id)
    if not profile:
        raise AppError(
            code=state.ERROR_JOB_NOT_FOUND,
            message="JD profile was not found.",
            status_code=404,
            details={"jd_id": jd_id},
        )
    context.resolved["job_profile_id"] = profile.id
    return StepResult(
        status=state.STEP_STATUS_COMPLETED,
        output_refs={
            "jd_id": jd_id,
            "job_profile_id": profile.id,
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
    return StepResult(
        status=state.STEP_STATUS_COMPLETED,
        output_refs={
            "match_report_id": report.match_report_id,
            "resume_version_id": report.resume_version_id,
            "jd_id": report.jd_id,
            "total_score": report.total_score,
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


def build_final_summary(db: Session, context: WorkflowContext) -> StepResult:
    resume_version_id = str(context.resolved["resume_version_id"])
    jd_id = str(context.resolved["jd_id"])
    match_report_id = str(context.resolved["match_report_id"])
    rag_source_count = int(context.resolved.get("rag_source_count") or 0)
    final_summary = (
        "Workflow completed using "
        f"resume_version_id={resume_version_id}, "
        f"jd_id={jd_id}, "
        f"match_report_id={match_report_id}, "
        f"rag_sources={rag_source_count}."
    )
    return StepResult(
        status=state.STEP_STATUS_COMPLETED,
        output_refs={
            "resume_version_id": resume_version_id,
            "jd_id": jd_id,
            "match_report_id": match_report_id,
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
    "build_final_summary": build_final_summary,
}
