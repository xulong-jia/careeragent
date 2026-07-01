from collections.abc import AsyncGenerator
from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.core.tenant import AuthContext, has_permission, reset_auth_context, set_auth_context
from app.db.session import get_db
from app.models.auth import RevokedToken, User, WorkspaceMembership
from app.services.audit_service import record_audit_event


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
    token_jti = str(payload.get("jti") or "")
    if token_jti and db.get(RevokedToken, token_jti):
        raise AppError(
            code="token_revoked",
            message="Authentication token has been revoked.",
            status_code=401,
            details={},
        )
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
    request: Request,
    user: User = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AsyncGenerator[AuthContext, None]:
    payload = decode_access_token(_extract_bearer_token(authorization))
    membership = db.get(WorkspaceMembership, (workspace_id, user.id))
    role = membership.role if membership else "viewer"
    context = AuthContext(
        user_id=user.id,
        workspace_id=workspace_id,
        email=user.email,
        role=role,
    )
    token = set_auth_context(context)
    try:
        _require_request_permission(request, role)
        audit_action = _audit_action_for_request(request.method.upper(), request.url.path)
        if audit_action:
            record_audit_event(
                db,
                action=audit_action,
                resource_type=_resource_type_for_path(request.url.path),
                resource_id=_resource_hint_for_path(request.url.path),
                metadata={"method": request.method.upper(), "path": request.url.path},
            )
        yield context
    finally:
        reset_auth_context(token)


def _require_request_permission(request: Request, role: str) -> None:
    permission = _permission_for_request(request.method.upper(), request.url.path)
    if permission and not has_permission(role, permission):
        raise AppError(
            code="workspace_permission_denied",
            message="Current workspace role cannot perform this action.",
            status_code=403,
            details={"permission": permission, "role": role},
        )


def _permission_for_request(method: str, path: str) -> str | None:
    if method == "GET":
        if path == "/api/privacy/audit-log":
            return "view_audit_logs"
        return "read_workspace_data"
    if path == "/api/privacy/delete-summary":
        return "privacy_delete"
    if path == "/api/privacy/delete-all":
        return "privacy_delete"
    if path.startswith("/api/resumes") or path.startswith("/api/resume-versions"):
        return "create_update_resume"
    if path.startswith("/api/jobs"):
        return "create_update_jd"
    if path.startswith("/api/matches"):
        return "run_match"
    if path.startswith("/api/agents"):
        return "run_agent"
    if path.startswith("/api/evaluations"):
        return "run_eval"
    if path.startswith("/api/bad-cases"):
        return "create_bad_case"
    if path.startswith("/api/privacy"):
        return "privacy_delete"
    return "workspace_write"


def _audit_action_for_request(method: str, path: str) -> str | None:
    if method == "GET" or path.startswith("/api/privacy"):
        return None
    if path.startswith("/api/resumes") or path.startswith("/api/resume-versions"):
        return f"resume.{method.lower()}"
    if path.startswith("/api/jobs"):
        return f"jd.{method.lower()}"
    if path.startswith("/api/rag/documents") and path.endswith("/index"):
        return "rag_document.index"
    if path.startswith("/api/rag/documents"):
        return f"rag_document.{method.lower()}"
    if path.startswith("/api/rag/answer"):
        return "rag_answer.create"
    if path.startswith("/api/matches/compare"):
        return "match.compare"
    if path.startswith("/api/matches"):
        return "match.run"
    if path.startswith("/api/agents"):
        return f"agent.{method.lower()}"
    if path.startswith("/api/evaluations"):
        return f"evaluation.{method.lower()}"
    if path.startswith("/api/bad-cases"):
        return f"bad_case.{method.lower()}"
    if path.startswith("/api/projects") or path.startswith("/api/project-rewrites"):
        return f"project.{method.lower()}"
    if path.startswith("/api/applications"):
        return f"application.{method.lower()}"
    if path.startswith("/api/interviews"):
        return f"interview.{method.lower()}"
    return f"workspace.{method.lower()}"


def _resource_type_for_path(path: str) -> str:
    parts = [part for part in path.split("/") if part]
    if len(parts) < 2:
        return "workspace"
    return parts[1].replace("-", "_")


def _resource_hint_for_path(path: str) -> str | None:
    parts = [part for part in path.split("/") if part]
    return parts[2] if len(parts) > 2 and not parts[2].startswith("?") else None
