from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.profile import Profile
from app.models.resume import ResumeVersion
from app.repositories import project_repository
from app.schemas.projects import (
    ProjectCreateRequest,
    ProjectRecord,
    ProjectStatus,
    ProjectUpdateRequest,
)


PRIVATE_TEXT_KEYS = {
    "raw_text",
    "raw_text_preview",
    "resume_text",
    "full_text",
    "source_text",
}


def create_project(db: Session, payload: ProjectCreateRequest) -> ProjectRecord:
    profile_id = _normalize_optional_id(payload.profile_id, "profile_id")
    resume_version_id = _normalize_optional_id(
        payload.resume_version_id, "resume_version_id"
    )
    _validate_profile(db, profile_id)
    _validate_resume_version(db, resume_version_id)
    evidence = _normalize_evidence(payload.evidence)
    return project_repository.create_project(
        db,
        profile_id=profile_id,
        resume_version_id=resume_version_id,
        name=_normalize_required_text(payload.name, "name"),
        role=_normalize_optional_text(payload.role, "role"),
        period=_normalize_optional_text(payload.period, "period"),
        background=_normalize_optional_text(payload.background, "background"),
        tech_stack=_normalize_string_list(payload.tech_stack, "tech_stack"),
        responsibilities=_normalize_string_list(
            payload.responsibilities, "responsibilities"
        ),
        results=_normalize_string_list(payload.results, "results"),
        evidence=evidence,
        status=payload.status,
    )


def list_projects(
    db: Session,
    *,
    profile_id: str | None = None,
    resume_version_id: str | None = None,
    status: ProjectStatus | None = None,
) -> list[ProjectRecord]:
    return project_repository.list_projects(
        db,
        profile_id=_normalize_optional_id(profile_id, "profile_id"),
        resume_version_id=_normalize_optional_id(
            resume_version_id, "resume_version_id"
        ),
        status=status,
    )


def get_project(db: Session, project_id: str) -> ProjectRecord:
    return project_repository.get_project(db, project_id)


def update_project(
    db: Session, project_id: str, payload: ProjectUpdateRequest
) -> ProjectRecord:
    if not payload.model_fields_set:
        raise AppError(
            code="validation_error",
            message="At least one project field must be provided.",
            status_code=400,
            details={"field": "project"},
        )

    project = project_repository.get_project_model(db, project_id)
    if not project:
        raise AppError(
            code="project_not_found",
            message="Project was not found.",
            status_code=404,
            details={"project_id": project_id},
        )

    updates: dict[str, object] = {}
    fields = payload.model_fields_set

    if "profile_id" in fields:
        profile_id = _normalize_optional_id(payload.profile_id, "profile_id")
        _validate_profile(db, profile_id)
        updates["profile_id"] = profile_id
    if "resume_version_id" in fields:
        resume_version_id = _normalize_optional_id(
            payload.resume_version_id, "resume_version_id"
        )
        _validate_resume_version(db, resume_version_id)
        updates["resume_version_id"] = resume_version_id
    if "name" in fields:
        updates["name"] = _normalize_required_text(payload.name or "", "name")
    if "role" in fields:
        updates["role"] = _normalize_optional_text(payload.role, "role")
    if "period" in fields:
        updates["period"] = _normalize_optional_text(payload.period, "period")
    if "background" in fields:
        updates["background"] = _normalize_optional_text(
            payload.background, "background"
        )
    if "tech_stack" in fields and payload.tech_stack is not None:
        updates["tech_stack"] = _normalize_string_list(
            payload.tech_stack, "tech_stack"
        )
    if "responsibilities" in fields and payload.responsibilities is not None:
        updates["responsibilities"] = _normalize_string_list(
            payload.responsibilities, "responsibilities"
        )
    if "results" in fields and payload.results is not None:
        updates["results"] = _normalize_string_list(payload.results, "results")
    if "evidence" in fields and payload.evidence is not None:
        updates["evidence"] = _normalize_evidence(payload.evidence)
    if "status" in fields and payload.status is not None:
        updates["status"] = payload.status

    return project_repository.update_project(db, project, updates=updates)


def _validate_profile(db: Session, profile_id: str | None) -> None:
    if profile_id is None:
        return
    if db.get(Profile, profile_id) is None:
        raise AppError(
            code="profile_not_found",
            message="Profile was not found.",
            status_code=404,
            details={"profile_id": profile_id},
        )


def _validate_resume_version(db: Session, resume_version_id: str | None) -> None:
    if resume_version_id is None:
        return
    if db.get(ResumeVersion, resume_version_id) is None:
        raise AppError(
            code="resume_version_not_found",
            message="Resume version was not found.",
            status_code=404,
            details={"version_id": resume_version_id},
        )


def _normalize_optional_id(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise AppError(
            code="validation_error",
            message=f"{field_name} must not be empty.",
            status_code=400,
            details={"field": field_name},
        )
    return normalized


def _normalize_required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise AppError(
            code="validation_error",
            message=f"{field_name} is required.",
            status_code=400,
            details={"field": field_name},
        )
    return normalized


def _normalize_optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized


def _normalize_string_list(values: list[str], field_name: str) -> list[str]:
    normalized: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned:
            raise AppError(
                code="validation_error",
                message=f"{field_name} must not contain empty strings.",
                status_code=400,
                details={"field": field_name},
            )
        normalized.append(cleaned)
    return normalized


def _normalize_evidence(
    evidence_items: list[dict[str, object]]
) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for item in evidence_items:
        _reject_private_text_keys(item)
        normalized.append(dict(item))
    return normalized


def _reject_private_text_keys(value: object) -> None:
    if isinstance(value, dict):
        if PRIVATE_TEXT_KEYS.intersection(value):
            raise AppError(
                code="validation_error",
                message="Evidence must not include raw private text fields.",
                status_code=400,
                details={"forbidden_fields": sorted(PRIVATE_TEXT_KEYS.intersection(value))},
            )
        for child in value.values():
            _reject_private_text_keys(child)
    elif isinstance(value, list):
        for child in value:
            _reject_private_text_keys(child)
