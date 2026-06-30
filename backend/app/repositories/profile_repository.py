from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.tenant import (
    current_user_id,
    current_workspace_id,
    is_owned,
    owner_filter,
)
from app.models.profile import Profile
from app.schemas.profiles import ProfileRecord


def _next_profile_id(db: Session) -> str:
    for _ in range(10):
        profile_id = f"profile_{uuid4().hex[:12]}"
        if db.get(Profile, profile_id) is None:
            return profile_id
    raise AppError(
        code="profile_id_generation_failed",
        message="Unable to generate a unique profile id.",
        status_code=500,
        details={},
    )


def _to_profile_record(profile: Profile) -> ProfileRecord:
    return ProfileRecord(
        id=profile.id,
        user_id=profile.user_id,
        target_roles=list(profile.target_roles or []),
        target_industries=list(profile.target_industries or []),
        target_locations=list(profile.target_locations or []),
        skill_map=dict(profile.skill_map or {}),
        preferences=dict(profile.preferences or {}),
        source_resume_version_id=profile.source_resume_version_id,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def create_profile(
    db: Session,
    *,
    target_roles: list[str],
    target_industries: list[str],
    target_locations: list[str],
    skill_map: dict[str, object],
    preferences: dict[str, object],
    source_resume_version_id: str | None,
) -> ProfileRecord:
    profile = Profile(
        id=_next_profile_id(db),
        user_id=current_user_id(),
        workspace_id=current_workspace_id(),
        target_roles=target_roles,
        target_industries=target_industries,
        target_locations=target_locations,
        skill_map=skill_map,
        preferences=preferences,
        source_resume_version_id=source_resume_version_id,
    )
    try:
        db.add(profile)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(profile)
    return _to_profile_record(profile)


def list_profiles(db: Session) -> list[ProfileRecord]:
    profiles = db.scalars(
        select(Profile)
        .where(*owner_filter(Profile))
        .order_by(Profile.created_at, Profile.id)
    ).all()
    return [_to_profile_record(profile) for profile in profiles]


def get_profile_model(db: Session, profile_id: str) -> Profile | None:
    profile = db.get(Profile, profile_id)
    return profile if profile and is_owned(profile) else None


def get_profile(db: Session, profile_id: str) -> ProfileRecord:
    profile = get_profile_model(db, profile_id)
    if not profile:
        raise AppError(
            code="profile_not_found",
            message="Profile was not found.",
            status_code=404,
            details={"profile_id": profile_id},
        )
    return _to_profile_record(profile)


def update_profile(
    db: Session,
    profile: Profile,
    *,
    target_roles: list[str] | None = None,
    target_industries: list[str] | None = None,
    target_locations: list[str] | None = None,
    skill_map: dict[str, object] | None = None,
    preferences: dict[str, object] | None = None,
    source_resume_version_id: str | None = None,
    clear_source_resume_version_id: bool = False,
) -> ProfileRecord:
    if target_roles is not None:
        profile.target_roles = target_roles
    if target_industries is not None:
        profile.target_industries = target_industries
    if target_locations is not None:
        profile.target_locations = target_locations
    if skill_map is not None:
        profile.skill_map = skill_map
    if preferences is not None:
        profile.preferences = preferences
    if clear_source_resume_version_id:
        profile.source_resume_version_id = None
    elif source_resume_version_id is not None:
        profile.source_resume_version_id = source_resume_version_id

    try:
        db.add(profile)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(profile)
    return _to_profile_record(profile)
