import json
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy.orm import Session
from backend.core.logging_config import app_logger
from backend.database.sqlite_db import AuditLog, User

SENSITIVE_AUDIT_KEYS = {
    "password",
    "password_hash",
    "secret",
    "token",
    "access_token",
    "authorization",
    "raw_content",
    "content",
}


def sanitize_audit_details(details: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not details:
        return {}
    clean: dict[str, Any] = {}
    for k, v in details.items():
        if k.lower() in SENSITIVE_AUDIT_KEYS:
            continue
        if isinstance(v, (str, int, float, bool)) or v is None:
            clean[k] = v
        elif isinstance(v, (list, dict)):
            clean[k] = v
        else:
            clean[k] = str(v)
    return clean


def record_audit_log(
    db: Session,
    action: str,
    resource_type: str,
    user: Optional[User] = None,
    username: Optional[str] = None,
    user_role: Optional[str] = None,
    resource_id: Optional[str] = None,
    success: bool = True,
    severity: str = "INFO",
    ip_address: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    workspace_id: Optional[str] = None,
) -> AuditLog:
    """
    Record a security-sensitive action in the local SQLite audit_logs table,
    scoped to the workplace (`workspace_id`).
    Never logs passwords, tokens, or raw confidential document text.
    """
    safe_details = sanitize_audit_details(details)
    resolved_workspace_id = workspace_id or (user.workspace_id if user else None)
    entry = AuditLog(
        workspace_id=resolved_workspace_id,
        timestamp=datetime.now(timezone.utc),
        user_id=user.id if user else None,
        username=user.username if user else (username or "anonymous"),
        user_role=user.normalized_role if user else (user_role or "unauthenticated"),
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        success=success,
        severity=severity,
        ip_address=ip_address or "127.0.0.1",
        details_json=json.dumps(safe_details),
    )
    db.add(entry)
    db.commit()
    app_logger.info(
        f"[AUDIT] workplace={resolved_workspace_id} action={action} user={entry.username} role={entry.user_role} "
        f"resource={resource_type}:{resource_id} success={success} severity={severity}"
    )
    return entry
