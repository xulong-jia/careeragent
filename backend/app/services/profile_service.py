from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.tenant import require_owned
from app.models.resume import Resume, ResumeVersion
from app.repositories import profile_repository
from app.schemas.profiles import (
    ProfileCreateRequest,
    ProfileRecord,
    ProfileSummary,
    ProfileUpdateRequest,
)


def create_profile(db: Session, payload: ProfileCreateRequest) -> ProfileRecord:
    target_roles = _normalize_string_list(payload.target_roles, "target_roles")
    target_industries = _normalize_string_list(
        payload.target_industries, "target_industries"
    )
    target_locations = _normalize_string_list(
        payload.target_locations, "target_locations"
    )
    source_resume_version_id = _normalize_optional_source_resume_version_id(
        payload.source_resume_version_id
    )
    _validate_source_resume_version(db, source_resume_version_id)
    return profile_repository.create_profile(
        db,
        target_roles=target_roles,
        target_industries=target_industries,
        target_locations=target_locations,
        skill_map=payload.skill_map,
        preferences=payload.preferences,
        source_resume_version_id=source_resume_version_id,
    )


def list_profiles(db: Session) -> list[ProfileRecord]:
    return profile_repository.list_profiles(db)


def get_profile(db: Session, profile_id: str) -> ProfileRecord:
    return profile_repository.get_profile(db, profile_id)


def update_profile(
    db: Session, profile_id: str, payload: ProfileUpdateRequest
) -> ProfileRecord:
    profile = profile_repository.get_profile_model(db, profile_id)
    if not profile:
        raise AppError(
            code="profile_not_found",
            message="Profile was not found.",
            status_code=404,
            details={"profile_id": profile_id},
        )

    fields = payload.model_fields_set
    source_resume_version_id: str | None = None
    clear_source_resume_version_id = False
    if "source_resume_version_id" in fields:
        if payload.source_resume_version_id is None:
            clear_source_resume_version_id = True
        else:
            source_resume_version_id = _normalize_optional_source_resume_version_id(
                payload.source_resume_version_id
            )
            _validate_source_resume_version(db, source_resume_version_id)

    return profile_repository.update_profile(
        db,
        profile,
        target_roles=(
            _normalize_string_list(payload.target_roles, "target_roles")
            if "target_roles" in fields and payload.target_roles is not None
            else None
        ),
        target_industries=(
            _normalize_string_list(payload.target_industries, "target_industries")
            if "target_industries" in fields and payload.target_industries is not None
            else None
        ),
        target_locations=(
            _normalize_string_list(payload.target_locations, "target_locations")
            if "target_locations" in fields and payload.target_locations is not None
            else None
        ),
        skill_map=payload.skill_map if "skill_map" in fields else None,
        preferences=payload.preferences if "preferences" in fields else None,
        source_resume_version_id=source_resume_version_id,
        clear_source_resume_version_id=clear_source_resume_version_id,
    )


def summarize_profile(db: Session, profile_id: str) -> ProfileSummary:
    profile = get_profile(db, profile_id)
    missing_fields: list[str] = []
    score = 0

    if profile.target_roles:
        score += 35
    else:
        missing_fields.append("target_roles")

    if profile.target_locations:
        score += 30
    else:
        missing_fields.append("target_locations")

    skill_categories_count = _skill_categories_count(profile.skill_map)
    if skill_categories_count:
        score += 35
    else:
        missing_fields.append("skill_map")

    if profile.source_resume_version_id:
        score = min(score + 10, 100)

    if score < 60:
        readiness_level = "incomplete"
    elif score < 100:
        readiness_level = "basic"
    else:
        readiness_level = "ready"

    return ProfileSummary(
        profile_id=profile.id,
        completeness_score=score,
        missing_fields=missing_fields,
        target_roles_count=len(profile.target_roles),
        target_locations_count=len(profile.target_locations),
        skill_categories_count=skill_categories_count,
        source_resume_version_id=profile.source_resume_version_id,
        readiness_level=readiness_level,
    )


def _validate_source_resume_version(
    db: Session, source_resume_version_id: str | None
) -> None:
    if source_resume_version_id is None:
        return
    version = db.get(ResumeVersion, source_resume_version_id)
    resume = db.get(Resume, version.resume_id) if version else None
    require_owned(
        resume,
        code="resume_version_not_found",
        message="Resume version was not found.",
        details={"version_id": source_resume_version_id},
    )
    if version is None:
        raise AppError(
            code="resume_version_not_found",
            message="Resume version was not found.",
            status_code=404,
            details={"version_id": source_resume_version_id},
        )


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


def _normalize_optional_source_resume_version_id(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise AppError(
            code="validation_error",
            message="source_resume_version_id must not be empty.",
            status_code=400,
            details={"field": "source_resume_version_id"},
        )
    return normalized


def _skill_categories_count(skill_map: dict[str, object]) -> int:
    count = 0
    for value in skill_map.values():
        if _has_skill_value(value):
            count += 1
    return count


def _has_skill_value(value: object) -> bool:
    if isinstance(value, list):
        return any(str(item).strip() for item in value)
    if isinstance(value, dict):
        return any(_has_skill_value(item) for item in value.values())
    if isinstance(value, str):
        return bool(value.strip())
    return value is not None
