from dataclasses import dataclass
from contextvars import ContextVar, Token

from app.core.errors import AppError


DEFAULT_USER_ID = "default"
DEFAULT_WORKSPACE_ID = "default_workspace"


@dataclass(frozen=True)
class AuthContext:
    user_id: str
    workspace_id: str
    email: str
    role: str


_auth_context: ContextVar[AuthContext | None] = ContextVar(
    "auth_context",
    default=None,
)


def set_auth_context(context: AuthContext) -> Token[AuthContext | None]:
    return _auth_context.set(context)


def reset_auth_context(token: Token[AuthContext | None]) -> None:
    _auth_context.reset(token)


def get_auth_context() -> AuthContext | None:
    return _auth_context.get()


def current_user_id() -> str:
    context = get_auth_context()
    return context.user_id if context else DEFAULT_USER_ID


def current_workspace_id() -> str:
    context = get_auth_context()
    return context.workspace_id if context else DEFAULT_WORKSPACE_ID


def owner_filter(model):
    return (
        model.user_id == current_user_id(),
        model.workspace_id == current_workspace_id(),
    )


ROLE_PERMISSIONS = {
    "owner": {
        "read_workspace_data",
        "workspace_write",
        "create_update_resume",
        "create_update_jd",
        "run_match",
        "run_agent",
        "run_eval",
        "create_bad_case",
        "privacy_delete",
        "manage_members",
        "view_audit_logs",
    },
    "admin": {
        "read_workspace_data",
        "workspace_write",
        "create_update_resume",
        "create_update_jd",
        "run_match",
        "run_agent",
        "run_eval",
        "create_bad_case",
        "privacy_delete",
        "manage_members",
        "view_audit_logs",
    },
    "member": {
        "read_workspace_data",
        "workspace_write",
        "create_update_resume",
        "create_update_jd",
        "run_match",
        "run_agent",
        "run_eval",
        "create_bad_case",
    },
    "viewer": {"read_workspace_data"},
}


def has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())


def require_permission(permission: str) -> None:
    context = get_auth_context()
    role = context.role if context else ""
    if not has_permission(role, permission):
        raise AppError(
            code="workspace_permission_denied",
            message="Current workspace role cannot perform this action.",
            status_code=403,
            details={"permission": permission, "role": role},
        )


def is_owned(record: object) -> bool:
    return (
        getattr(record, "user_id", DEFAULT_USER_ID) == current_user_id()
        and getattr(record, "workspace_id", DEFAULT_WORKSPACE_ID)
        == current_workspace_id()
    )


def require_owned(
    record: object | None,
    *,
    code: str,
    message: str,
    details: dict[str, object],
) -> None:
    if record is None or not is_owned(record):
        raise AppError(code=code, message=message, status_code=404, details=details)
