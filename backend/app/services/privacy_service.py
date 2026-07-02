from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_text
from app.core.privacy import safe_preview
from app.core.tenant import current_user_id, current_workspace_id, owner_filter, require_permission
from app.models.auth import AuditLog, User, WorkspaceMembership
from app.models.agent import AgentRun, AgentStep
from app.models.application import Application, ApplicationStatusHistory
from app.models.evaluation import BadCase, EvaluationCase, EvaluationResult, EvaluationRun
from app.models.interview import InterviewAnswer, InterviewQuestion
from app.models.job import JobDescription, JobProfile
from app.models.match import MatchReport
from app.models.profile import Profile
from app.models.project import Project, ProjectRewrite
from app.models.rag import RagAnswerRun, RagChunk, RagDocument
from app.models.resume import Resume, ResumeVersion
from app.models.study_plan import StudyPlan
from app.services.audit_service import record_audit_event

LEGAL_HOLD_RESOURCE_TYPE = "privacy_legal_hold"
LEGAL_HOLD_STATUS_ACTION = "privacy.legal_hold_status"


def _count(db: Session, model) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*owner_filter(model))) or 0


def _count_where(db: Session, model, *where) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*where)) or 0


def _scoped_counts(db: Session) -> dict[str, int]:
    resume_ids = select(Resume.id).where(*owner_filter(Resume))
    job_ids = select(JobDescription.id).where(*owner_filter(JobDescription))
    application_ids = select(Application.id).where(*owner_filter(Application))
    rag_doc_ids = select(RagDocument.id).where(*owner_filter(RagDocument))
    agent_run_ids = select(AgentRun.id).where(*owner_filter(AgentRun))
    question_ids = select(InterviewQuestion.id).where(*owner_filter(InterviewQuestion))
    eval_run_ids = select(EvaluationRun.id).where(*owner_filter(EvaluationRun))
    eval_case_ids = select(EvaluationCase.id).where(*owner_filter(EvaluationCase))
    return {
        "users": _count_where(db, User, User.id == current_user_id()),
        "workspace_memberships": _count_where(
            db,
            WorkspaceMembership,
            WorkspaceMembership.user_id == current_user_id(),
            WorkspaceMembership.workspace_id == current_workspace_id(),
        ),
        "profiles": _count(db, Profile),
        "resumes": _count(db, Resume),
        "resume_versions": _count_where(db, ResumeVersion, ResumeVersion.resume_id.in_(resume_ids)),
        "job_descriptions": _count(db, JobDescription),
        "job_profiles": _count_where(db, JobProfile, JobProfile.jd_id.in_(job_ids)),
        "match_reports": _count(db, MatchReport),
        "projects": _count(db, Project),
        "project_rewrites": _count(db, ProjectRewrite),
        "interview_questions": _count(db, InterviewQuestion),
        "interview_answers": _count(db, InterviewAnswer),
        "study_plans": _count(db, StudyPlan),
        "applications": _count(db, Application),
        "application_status_history": _count_where(
            db,
            ApplicationStatusHistory,
            ApplicationStatusHistory.application_id.in_(application_ids),
        ),
        "rag_documents": _count(db, RagDocument),
        "rag_chunks": _count_where(db, RagChunk, RagChunk.document_id.in_(rag_doc_ids)),
        "rag_answer_runs": _count(db, RagAnswerRun),
        "agent_runs": _count(db, AgentRun),
        "agent_steps": _count_where(db, AgentStep, AgentStep.run_id.in_(agent_run_ids)),
        "bad_cases": _count(db, BadCase),
        "evaluation_runs": _count(db, EvaluationRun),
        "evaluation_cases": _count(db, EvaluationCase),
        "evaluation_results": _count(db, EvaluationResult),
    }


def deletion_summary_current_user_data(db: Session) -> dict[str, object]:
    require_permission("privacy_delete")
    counts = _scoped_counts(db)
    return {
        "status": "summary",
        "user_id": current_user_id(),
        "workspace_id": current_workspace_id(),
        "resources": counts,
        "total_records": sum(counts.values()),
        "retention_note": (
            "This summary covers active database rows in the current workspace. "
            "It is not proof of backup purge or external retention deletion."
        ),
        "backup_purge_status": "not_implemented",
    }


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
                "raw_text_preview": safe_preview(decrypt_text(item.raw_text)),
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
                "raw_text_preview": safe_preview(decrypt_text(item.raw_text)),
            }
            for item in rag_documents
        ],
        "rag_answer_runs": [
            {"id": item.id, "question_preview": safe_preview(decrypt_text(item.question))}
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


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _build_retained_records() -> list[dict[str, object]]:
    return [
        {
            "resource_type": "audit_logs",
            "retention_reason": "redacted audit tombstone retained for governance trail",
        },
        {
            "resource_type": "users",
            "retention_reason": "auth account retained; v3.0 deletes workspace data, not identity account",
        },
        {
            "resource_type": "workspace_memberships",
            "retention_reason": "current membership retained to preserve access to deletion proof and audit trail",
        },
    ]


def set_legal_hold_for_current_subject(
    db: Session,
    *,
    active: bool,
    reason: str = "policy_control",
) -> AuditLog:
    return record_audit_event(
        db,
        action=LEGAL_HOLD_STATUS_ACTION,
        resource_type=LEGAL_HOLD_RESOURCE_TYPE,
        resource_id=current_user_id(),
        metadata={
            "active": active,
            "reason": reason,
            "scope": "current_user_workspace",
        },
    )


def _legal_hold_state(db: Session) -> dict[str, object]:
    log = db.scalars(
        select(AuditLog)
        .where(AuditLog.user_id == current_user_id())
        .where(AuditLog.workspace_id == current_workspace_id())
        .where(AuditLog.action == LEGAL_HOLD_STATUS_ACTION)
        .where(AuditLog.resource_type == LEGAL_HOLD_RESOURCE_TYPE)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(1)
    ).first()
    if log is None:
        return {"active": False, "source_audit_event_id": None}
    metadata = dict(log.metadata_json or {})
    return {
        "active": metadata.get("active") is True,
        "source_audit_event_id": log.id,
        "scope": metadata.get("scope", "current_user_workspace"),
    }


def _proof_payload(
    *,
    status: str,
    proof_id: str,
    started_at: datetime,
    finished_at: datetime,
    counts: dict[str, int],
    audit_event_id: str | None,
    legal_hold_state: dict[str, object] | None = None,
) -> dict[str, object]:
    legal_hold_state = legal_hold_state or {"active": False, "source_audit_event_id": None}
    legal_hold_active = legal_hold_state.get("active") is True
    deleted_counts = {
        key: (
            0
            if status in {"dry_run", "legal_hold_blocked"}
            or key in {"users", "workspace_memberships"}
            else value
        )
        for key, value in counts.items()
    }
    backup_purge_status = "legal_hold" if legal_hold_active else "not_implemented"
    verification_status = (
        "legal_hold_blocked"
        if status == "legal_hold_blocked"
        else "dry_run_not_deleted"
        if status == "dry_run"
        else "database_rows_deleted"
    )
    return {
        "status": status,
        "deletion_proof_id": proof_id,
        "user_id": current_user_id(),
        "workspace_id": current_workspace_id(),
        "requested_by": current_user_id(),
        "started_at": started_at,
        "finished_at": finished_at,
        "resource_counts_before": counts,
        "deleted_counts": deleted_counts,
        "retained_records": _build_retained_records(),
        "retention_reason": (
            "Legal hold is active; workspace business data was not deleted."
            if legal_hold_active
            else "Workspace business data is deleted; account, membership and redacted audit tombstone are retained."
        ),
        "retention_note": (
            "Database rows are scoped to the current workspace. This proof does not purge backups, logs, exports, or external systems."
        ),
        "backup_purge_status": backup_purge_status,
        "backup_purge_note": (
            "Legal hold blocks purge-complete marking until the hold is released."
            if legal_hold_active
            else "v3.1 defines retention/backup policy and restore runbooks, but automated managed-backup purge is not implemented."
        ),
        "legal_hold_status": "active" if legal_hold_active else "none",
        "legal_hold_blocked": legal_hold_active,
        "legal_hold_source_audit_event_id": legal_hold_state.get("source_audit_event_id"),
        "audit_event_id": audit_event_id,
        "verification_status": verification_status,
    }


def delete_current_user_data(db: Session, *, dry_run: bool = False) -> dict[str, object]:
    require_permission("privacy_delete")
    user_id = current_user_id()
    counts = _scoped_counts(db)
    proof_id = f"deletion_{uuid4().hex[:12]}"
    started_at = _now()
    action = "privacy.delete_dry_run" if dry_run else "privacy.delete_execute"
    legal_hold_state = _legal_hold_state(db)

    if legal_hold_state.get("active") is True:
        audit = record_audit_event(
            db,
            action=f"{action}_legal_hold_blocked",
            resource_type="privacy",
            resource_id=user_id,
            metadata={
                "deletion_proof_id": proof_id,
                "resource_counts_before": counts,
                "legal_hold_status": "active",
                "legal_hold_source_audit_event_id": legal_hold_state.get(
                    "source_audit_event_id"
                ),
                "dry_run": dry_run,
            },
        )
        db.commit()
        return _proof_payload(
            status="legal_hold_blocked",
            proof_id=proof_id,
            started_at=started_at,
            finished_at=_now(),
            counts=counts,
            audit_event_id=audit.id,
            legal_hold_state=legal_hold_state,
        )

    if dry_run:
        audit = record_audit_event(
            db,
            action=action,
            resource_type="privacy",
            resource_id=user_id,
            metadata={"deletion_proof_id": proof_id, "resource_counts_before": counts},
        )
        db.commit()
        finished_at = _now()
        return _proof_payload(
            status="dry_run",
            proof_id=proof_id,
            started_at=started_at,
            finished_at=finished_at,
            counts=counts,
            audit_event_id=audit.id,
            legal_hold_state=legal_hold_state,
        )

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
        audit = record_audit_event(
            db,
            action=action,
            resource_type="privacy",
            resource_id=current_user_id(),
            metadata={
                "deletion_proof_id": proof_id,
                "resource_counts_before": counts,
                "deleted_counts": {
                    key: value for key, value in counts.items() if key not in {"users", "workspace_memberships"}
                },
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return _proof_payload(
        status="deleted",
        proof_id=proof_id,
        started_at=started_at,
        finished_at=_now(),
        counts=counts,
        audit_event_id=audit.id,
        legal_hold_state=legal_hold_state,
    )


def list_audit_logs(db: Session) -> list[dict[str, object]]:
    require_permission("view_audit_logs")
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
