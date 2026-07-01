from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.privacy import redact_mapping
from app.core.tenant import current_user_id, current_workspace_id
from app.models.auth import AuditLog


def _next_audit_id(db: Session) -> str:
    for _ in range(10):
        candidate = f"audit_{uuid4().hex[:12]}"
        if db.get(AuditLog, candidate) is None:
            return candidate
    return f"audit_{uuid4().hex}"


def record_audit_event(
    db: Session,
    *,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    metadata: dict[str, object] | None = None,
    user_id: str | None = None,
    workspace_id: str | None = None,
) -> AuditLog:
    log = AuditLog(
        id=_next_audit_id(db),
        user_id=user_id or current_user_id(),
        workspace_id=workspace_id or current_workspace_id(),
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json=redact_mapping(metadata or {}),
        message="Audit event recorded.",
    )
    db.add(log)
    return log
