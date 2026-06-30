from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.tenant import (
    current_user_id,
    current_workspace_id,
    owner_filter,
    require_owned,
)
from app.models.match import MatchReport as MatchReportModel
from app.schemas.matches import MatchEvidence, MatchReport


def _next_match_report_id(db: Session) -> str:
    count = db.scalar(select(func.count()).select_from(MatchReportModel)) or 0
    return f"match_{count + 1:04d}"


def _to_match_report(record: MatchReportModel) -> MatchReport:
    return MatchReport(
        match_report_id=record.id,
        resume_id=record.resume_version.resume_id,
        resume_version_id=record.resume_version_id,
        jd_id=record.jd_id,
        job_profile_id=record.job_profile_id,
        total_score=record.total_score,
        dimension_scores=dict(record.dimension_scores or {}),
        evidence=[
            MatchEvidence.model_validate(item) for item in list(record.evidence or [])
        ],
        strengths=list(record.strengths or []),
        gaps=list(record.gaps or []),
        rewrite_priorities=list(record.rewrite_priorities or []),
        risk_flags=list(record.risk_flags or []),
        created_at=record.created_at,
    )


def create_match_report(
    db: Session,
    *,
    resume_version_id: str,
    jd_id: str,
    job_profile_id: str | None,
    total_score: int,
    dimension_scores: dict[str, int],
    evidence: list[MatchEvidence],
    strengths: list[str],
    gaps: list[str],
    rewrite_priorities: list[str],
    risk_flags: list[dict[str, object]],
) -> MatchReport:
    record = MatchReportModel(
        id=_next_match_report_id(db),
        user_id=current_user_id(),
        workspace_id=current_workspace_id(),
        resume_version_id=resume_version_id,
        jd_id=jd_id,
        job_profile_id=job_profile_id,
        total_score=total_score,
        dimension_scores=dimension_scores,
        evidence=[item.model_dump() for item in evidence],
        strengths=strengths,
        gaps=gaps,
        rewrite_priorities=rewrite_priorities,
        risk_flags=risk_flags,
    )

    try:
        db.add(record)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(record)
    return _to_match_report(record)


def list_match_reports(
    db: Session,
    *,
    jd_id: str | None = None,
    resume_version_id: str | None = None,
) -> list[MatchReport]:
    statement = (
        select(MatchReportModel)
        .where(*owner_filter(MatchReportModel))
        .order_by(MatchReportModel.created_at, MatchReportModel.id)
    )
    if jd_id:
        statement = statement.where(MatchReportModel.jd_id == jd_id)
    if resume_version_id:
        statement = statement.where(MatchReportModel.resume_version_id == resume_version_id)

    records = db.scalars(statement).all()
    return [_to_match_report(record) for record in records]


def list_match_reports_by_jd_id(db: Session, jd_id: str) -> list[MatchReport]:
    return list_match_reports(db, jd_id=jd_id)


def list_match_reports_by_resume_version_id(
    db: Session, resume_version_id: str
) -> list[MatchReport]:
    return list_match_reports(db, resume_version_id=resume_version_id)


def get_match_report(db: Session, match_report_id: str) -> MatchReport:
    record = db.get(MatchReportModel, match_report_id)
    require_owned(
        record,
        code="match_report_not_found",
        message="Match report was not found.",
        details={"match_report_id": match_report_id},
    )
    if not record:
        raise AppError(
            code="match_report_not_found",
            message="Match report was not found.",
            status_code=404,
            details={"match_report_id": match_report_id},
        )
    return _to_match_report(record)
