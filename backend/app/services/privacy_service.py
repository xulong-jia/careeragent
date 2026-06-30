from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.privacy import safe_preview
from app.core.tenant import current_user_id, current_workspace_id, owner_filter
from app.models.agent import AgentRun, AgentStep
from app.models.application import Application, ApplicationStatusHistory
from app.models.auth import AuditLog
from app.models.evaluation import BadCase, EvaluationCase, EvaluationResult, EvaluationRun
from app.models.interview import InterviewAnswer, InterviewQuestion
from app.models.job import JobDescription, JobProfile
from app.models.match import MatchReport
from app.models.profile import Profile
from app.models.project import Project, ProjectRewrite
from app.models.rag import RagAnswerRun, RagChunk, RagDocument
from app.models.resume import Resume, ResumeVersion
from app.models.study_plan import StudyPlan


def _next_audit_id(db: Session) -> str:
    for _ in range(10):
        candidate = f"audit_{uuid4().hex[:12]}"
        if db.get(AuditLog, candidate) is None:
            return candidate
    return f"audit_{uuid4().hex}"


def _count(db: Session, model) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*owner_filter(model))) or 0


def _audit(db: Session, action: str, metadata: dict[str, object]) -> AuditLog:
    log = AuditLog(
        id=_next_audit_id(db),
        user_id=current_user_id(),
        workspace_id=current_workspace_id(),
        action=action,
        resource_type="privacy",
        resource_id=current_user_id(),
        metadata_json=metadata,
        message="Privacy operation completed.",
    )
    db.add(log)
    return log


def export_current_user_data(db: Session) -> dict[str, object]:
    user_id = current_user_id()
    workspace_id = current_workspace_id()
    resumes = db.scalars(select(Resume).where(*owner_filter(Resume))).all()
    jobs = db.scalars(select(JobDescription).where(*owner_filter(JobDescription))).all()
    rag_documents = db.scalars(select(RagDocument).where(*owner_filter(RagDocument))).all()
    audit_logs = db.scalars(
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .where(AuditLog.workspace_id == workspace_id)
        .order_by(AuditLog.created_at, AuditLog.id)
    ).all()
    return {
        "user_id": user_id,
        "workspace_id": workspace_id,
        "profiles": [
            {"id": item.id, "target_roles": list(item.target_roles or [])}
            for item in db.scalars(select(Profile).where(*owner_filter(Profile))).all()
        ],
        "resumes": [
            {"id": item.id, "title": item.title, "status": item.status}
            for item in resumes
        ],
        "jobs": [
            {
                "id": item.id,
                "company": item.company,
                "job_title": item.job_title,
                "raw_text_preview": safe_preview(item.raw_text),
            }
            for item in jobs
        ],
        "matches": [
            {"id": item.id, "jd_id": item.jd_id, "resume_version_id": item.resume_version_id}
            for item in db.scalars(select(MatchReport).where(*owner_filter(MatchReport))).all()
        ],
        "applications": [
            {"id": item.id, "company": item.company, "status": item.status}
            for item in db.scalars(select(Application).where(*owner_filter(Application))).all()
        ],
        "rag_documents": [
            {
                "id": item.id,
                "title": item.title,
                "source_type": item.source_type,
                "raw_text_preview": safe_preview(item.raw_text),
            }
            for item in rag_documents
        ],
        "rag_answer_runs": [
            {"id": item.id, "question_preview": safe_preview(item.question)}
            for item in db.scalars(select(RagAnswerRun).where(*owner_filter(RagAnswerRun))).all()
        ],
        "agent_runs": [
            {"id": item.id, "workflow_name": item.workflow_name, "status": item.status}
            for item in db.scalars(select(AgentRun).where(*owner_filter(AgentRun))).all()
        ],
        "bad_cases": [
            {"id": item.id, "title": item.title, "status": item.status}
            for item in db.scalars(select(BadCase).where(*owner_filter(BadCase))).all()
        ],
        "evaluation_runs": [
            {"id": item.id, "module": item.module, "status": item.status}
            for item in db.scalars(select(EvaluationRun).where(*owner_filter(EvaluationRun))).all()
        ],
        "audit_logs": [
            {
                "id": item.id,
                "action": item.action,
                "resource_type": item.resource_type,
                "metadata": dict(item.metadata_json or {}),
                "created_at": item.created_at,
            }
            for item in audit_logs
        ],
    }


def delete_current_user_data(db: Session) -> dict[str, object]:
    user_id = current_user_id()
    workspace_id = current_workspace_id()
    counts = {
        "profiles": _count(db, Profile),
        "resumes": _count(db, Resume),
        "jobs": _count(db, JobDescription),
        "matches": _count(db, MatchReport),
        "applications": _count(db, Application),
        "rag_documents": _count(db, RagDocument),
        "rag_answer_runs": _count(db, RagAnswerRun),
        "agent_runs": _count(db, AgentRun),
        "bad_cases": _count(db, BadCase),
        "evaluation_runs": _count(db, EvaluationRun),
    }

    resume_ids = select(Resume.id).where(*owner_filter(Resume))
    job_ids = select(JobDescription.id).where(*owner_filter(JobDescription))
    application_ids = select(Application.id).where(*owner_filter(Application))
    rag_doc_ids = select(RagDocument.id).where(*owner_filter(RagDocument))
    agent_run_ids = select(AgentRun.id).where(*owner_filter(AgentRun))
    question_ids = select(InterviewQuestion.id).where(*owner_filter(InterviewQuestion))
    eval_run_ids = select(EvaluationRun.id).where(*owner_filter(EvaluationRun))
    eval_case_ids = select(EvaluationCase.id).where(*owner_filter(EvaluationCase))

    try:
        db.execute(delete(ApplicationStatusHistory).where(ApplicationStatusHistory.application_id.in_(application_ids)))
        db.execute(delete(Application).where(*owner_filter(Application)))
        db.execute(delete(AgentStep).where(AgentStep.run_id.in_(agent_run_ids)))
        db.execute(delete(AgentRun).where(*owner_filter(AgentRun)))
        db.execute(delete(InterviewAnswer).where(InterviewAnswer.question_id.in_(question_ids)))
        db.execute(delete(InterviewAnswer).where(*owner_filter(InterviewAnswer)))
        db.execute(delete(InterviewQuestion).where(*owner_filter(InterviewQuestion)))
        db.execute(delete(StudyPlan).where(*owner_filter(StudyPlan)))
        db.execute(delete(ProjectRewrite).where(*owner_filter(ProjectRewrite)))
        db.execute(delete(Project).where(*owner_filter(Project)))
        db.execute(delete(EvaluationResult).where(EvaluationResult.run_id.in_(eval_run_ids)))
        db.execute(delete(EvaluationResult).where(EvaluationResult.case_id.in_(eval_case_ids)))
        db.execute(delete(EvaluationResult).where(*owner_filter(EvaluationResult)))
        db.execute(delete(EvaluationCase).where(*owner_filter(EvaluationCase)))
        db.execute(delete(EvaluationRun).where(*owner_filter(EvaluationRun)))
        db.execute(delete(BadCase).where(*owner_filter(BadCase)))
        db.execute(delete(RagChunk).where(RagChunk.document_id.in_(rag_doc_ids)))
        db.execute(delete(RagDocument).where(*owner_filter(RagDocument)))
        db.execute(delete(RagAnswerRun).where(*owner_filter(RagAnswerRun)))
        db.execute(delete(MatchReport).where(*owner_filter(MatchReport)))
        db.execute(delete(JobProfile).where(JobProfile.jd_id.in_(job_ids)))
        db.execute(delete(JobDescription).where(*owner_filter(JobDescription)))
        db.execute(delete(Profile).where(*owner_filter(Profile)))
        db.execute(delete(ResumeVersion).where(ResumeVersion.resume_id.in_(resume_ids)))
        db.execute(delete(Resume).where(*owner_filter(Resume)))
        _audit(db, "privacy.delete_all", {"deleted_counts": counts})
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {
        "status": "deleted",
        "user_id": user_id,
        "workspace_id": workspace_id,
        "deleted_counts": counts,
    }


def list_audit_logs(db: Session) -> list[dict[str, object]]:
    logs = db.scalars(
        select(AuditLog)
        .where(AuditLog.user_id == current_user_id())
        .where(AuditLog.workspace_id == current_workspace_id())
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    ).all()
    return [
        {
            "id": log.id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "metadata": dict(log.metadata_json or {}),
            "created_at": log.created_at,
        }
        for log in logs
    ]
