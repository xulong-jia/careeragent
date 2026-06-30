from collections.abc import AsyncGenerator

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.core.tenant import AuthContext, reset_auth_context, set_auth_context
from app.db.session import get_db
from app.models.auth import User, WorkspaceMembership


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise AppError(
            code="not_authenticated",
            message="Authentication is required.",
            status_code=401,
            details={},
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise AppError(
            code="invalid_authorization_header",
            message="Authorization header must use Bearer token.",
            status_code=401,
            details={},
        )
    return token.strip()


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(_extract_bearer_token(authorization))
    user_id = str(payload.get("sub") or "")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise AppError(
            code="invalid_token",
            message="Invalid or expired authentication token.",
            status_code=401,
            details={},
        )
    return user


def get_current_workspace_id(
    user: User = Depends(get_current_user),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> str:
    payload = decode_access_token(_extract_bearer_token(authorization))
    workspace_id = str(payload.get("workspace_id") or "")
    membership = db.get(WorkspaceMembership, (workspace_id, user.id))
    if not membership:
        raise AppError(
            code="workspace_forbidden",
            message="Current user cannot access this workspace.",
            status_code=403,
            details={},
        )
    return workspace_id


async def require_active_user(
    user: User = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
) -> AsyncGenerator[AuthContext, None]:
    context = AuthContext(
        user_id=user.id,
        workspace_id=workspace_id,
        email=user.email,
        role=user.role,
    )
    token = set_auth_context(context)
    try:
        yield context
    finally:
        reset_auth_context(token)
