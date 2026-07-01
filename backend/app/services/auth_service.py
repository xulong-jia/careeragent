import re
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.models.auth import RevokedToken, User, Workspace, WorkspaceMembership
from app.schemas.auth import (
    AuthLoginRequest,
    AuthMeResponse,
    AuthRegisterRequest,
    AuthTokenResponse,
    AuthUser,
    AuthWorkspace,
)
from app.services.audit_service import record_audit_event


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
AUTH_FAILED = AppError(
    code="invalid_credentials",
    message="Invalid email or password.",
    status_code=401,
    details={},
)


def normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if not EMAIL_RE.match(normalized):
        raise AppError(
            code="invalid_email",
            message="Email format is invalid.",
            status_code=400,
            details={"field": "email"},
        )
    return normalized


def _next_id(db: Session, model, prefix: str) -> str:
    for _ in range(10):
        candidate = f"{prefix}_{uuid4().hex[:12]}"
        if db.get(model, candidate) is None:
            return candidate
    raise AppError(
        code="id_generation_failed",
        message="Unable to generate a unique id.",
        status_code=500,
        details={"prefix": prefix},
    )


def _get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalars(select(User).where(func.lower(User.email) == email)).first()


def _get_default_workspace(db: Session, user_id: str) -> tuple[Workspace, str]:
    row = db.execute(
        select(Workspace, WorkspaceMembership.role)
        .join(
            WorkspaceMembership,
            WorkspaceMembership.workspace_id == Workspace.id,
        )
        .where(WorkspaceMembership.user_id == user_id)
        .order_by(Workspace.created_at, Workspace.id)
        .limit(1)
    ).first()
    if not row:
        raise AppError(
            code="workspace_not_found",
            message="Workspace was not found for current user.",
            status_code=403,
            details={},
        )
    workspace, role = row
    return workspace, str(role)


def _to_user(user: User) -> AuthUser:
    return AuthUser(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        is_active=user.is_active,
    )


def _to_workspace(workspace: Workspace, role: str) -> AuthWorkspace:
    return AuthWorkspace(id=workspace.id, name=workspace.name, role=role)


def _token_response(db: Session, user: User) -> AuthTokenResponse:
    workspace, workspace_role = _get_default_workspace(db, user.id)
    access_token, expires_at = create_access_token(
        subject=user.id,
        email=user.email,
        role=user.role,
        workspace_id=workspace.id,
    )
    return AuthTokenResponse(
        access_token=access_token,
        expires_at=expires_at,
        user=_to_user(user),
        workspace=_to_workspace(workspace, workspace_role),
    )


def register_user(db: Session, payload: AuthRegisterRequest) -> AuthTokenResponse:
    email = normalize_email(payload.email)
    if _get_user_by_email(db, email):
        raise AppError(
            code="email_already_registered",
            message="Email is already registered.",
            status_code=409,
            details={"field": "email"},
        )
    user = User(
        id=_next_id(db, User, "user"),
        email=email,
        password_hash=hash_password(payload.password),
        display_name=(payload.display_name or "").strip() or None,
        role="user",
        is_active=True,
    )
    workspace = Workspace(
        id=_next_id(db, Workspace, "workspace"),
        owner_user_id=user.id,
        name="Personal Workspace",
    )
    membership = WorkspaceMembership(
        workspace_id=workspace.id,
        user_id=user.id,
        role="owner",
    )
    try:
        db.add(user)
        db.add(workspace)
        db.add(membership)
        record_audit_event(
            db,
            action="auth.register",
            resource_type="user",
            resource_id=user.id,
            user_id=user.id,
            workspace_id=workspace.id,
            metadata={"workspace_id": workspace.id, "role": user.role},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(user)
    return _token_response(db, user)


def login_user(db: Session, payload: AuthLoginRequest) -> AuthTokenResponse:
    email = normalize_email(payload.email)
    user = _get_user_by_email(db, email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise AUTH_FAILED
    if not user.is_active:
        raise AUTH_FAILED
    workspace, _role = _get_default_workspace(db, user.id)
    record_audit_event(
        db,
        action="auth.login",
        resource_type="user",
        resource_id=user.id,
        user_id=user.id,
        workspace_id=workspace.id,
        metadata={},
    )
    db.commit()
    return _token_response(db, user)


def build_me_response(db: Session, user: User) -> AuthMeResponse:
    workspace, role = _get_default_workspace(db, user.id)
    return AuthMeResponse(user=_to_user(user), workspace=_to_workspace(workspace, role))


def logout_user(db: Session, *, token: str, user: User) -> dict[str, object]:
    payload = decode_access_token(token)
    token_jti = str(payload.get("jti") or "")
    workspace_id = str(payload.get("workspace_id") or "")
    if not token_jti:
        raise AppError(
            code="token_missing_jti",
            message="Authentication token cannot be revoked.",
            status_code=401,
            details={},
        )
    expires_at = datetime.fromtimestamp(int(payload.get("exp", 0)), tz=timezone.utc).replace(
        tzinfo=None
    )
    if db.get(RevokedToken, token_jti) is None:
        db.add(
            RevokedToken(
                token_jti=token_jti,
                user_id=user.id,
                workspace_id=workspace_id,
                expires_at=expires_at,
                reason="logout",
            )
        )
    record_audit_event(
        db,
        action="auth.logout",
        resource_type="user",
        resource_id=user.id,
        user_id=user.id,
        workspace_id=workspace_id,
        metadata={"token_jti": token_jti, "expires_at": expires_at},
    )
    record_audit_event(
        db,
        action="auth.token_revoke",
        resource_type="token",
        resource_id=token_jti,
        user_id=user.id,
        workspace_id=workspace_id,
        metadata={"reason": "logout", "expires_at": expires_at},
    )
    db.commit()
    return {"status": "logged_out", "token_revoked": True, "token_jti": token_jti}
