from __future__ import annotations

import uuid

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.audit import AuditLogRepository

# Canonical audit actions so strings stay consistent across the codebase.
ACTION_LOGIN = "auth.login"
ACTION_LOGIN_FAILED = "auth.login_failed"
ACTION_LOGOUT = "auth.logout"
ACTION_LOGOUT_ALL = "auth.logout_all"
ACTION_REFRESH = "auth.refresh"
ACTION_CHANGE_PASSWORD = "auth.change_password"
ACTION_FORGOT_PASSWORD = "auth.forgot_password"
ACTION_RESET_PASSWORD = "auth.reset_password"
ACTION_EMAIL_VERIFY_REQUEST = "auth.email_verify_requested"
ACTION_EMAIL_VERIFY = "auth.email_verified"
ACTION_SETTINGS_UPDATE = "settings.updated"
ACTION_API_KEY_CREATE = "api_key.created"
ACTION_API_KEY_REVOKE = "api_key.revoked"
ACTION_UPLOAD_CREATE = "upload.created"
ACTION_UPLOAD_DELETE = "upload.deleted"
ACTION_ADMIN = "admin.action"
ACTION_WEBHOOK = "webhook.event"
ACTION_SYSTEM_ERROR = "system.error"


def client_meta(request: Request | None) -> tuple[str | None, str | None]:
    """Extract (ip_address, user_agent) from a request, safely."""
    if request is None:
        return None, None
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return ip, user_agent


def log_action(
    db: Session,
    *,
    action: str,
    actor: User | None = None,
    actor_id=None,
    actor_type: str = "system",
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    result: str = "success",
    commit: bool = True,
) -> uuid.UUID:
    """Persist an audit entry on the given session.

    The session is expected to belong to the current request transaction;
    pass ``commit=True`` (default) when the caller has no other writes.
    """
    if actor is not None and actor_id is None:
        actor_id = actor.id
        actor_type = "user"
    repo = AuditLogRepository(db)
    entry = repo.record(
        action=action,
        actor_id=actor_id,
        actor_type=actor_type,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
        result=result,
    )
    if commit:
        db.commit()
    return entry.id


def log_action_from_request(
    db: Session,
    request: Request,
    *,
    action: str,
    actor: User | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict | None = None,
    result: str = "success",
) -> uuid.UUID:
    ip, user_agent = client_meta(request)
    return log_action(
        db,
        action=action,
        actor=actor,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip,
        user_agent=user_agent,
        result=result,
    )
