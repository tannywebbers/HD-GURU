from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.repositories.base import BaseRepository
from app.utils.pagination import Page


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog

    def record(
        self,
        *,
        action: str,
        actor_id=None,
        actor_type: str = "system",
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        result: str = "success",
    ) -> AuditLog:
        entry = AuditLog(
            actor_id=actor_id,
            actor_type=actor_type,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            result=result,
        )
        self.db.add(entry)
        return entry

    def list_recent(
        self,
        *,
        page: int = 1,
        per_page: int = 20,
        actor_id=None,
        action: str | None = None,
    ) -> Page[AuditLog]:
        stmt = select(AuditLog)
        if actor_id is not None:
            stmt = stmt.where(AuditLog.actor_id == actor_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        stmt = stmt.order_by(AuditLog.created_at.desc())
        return self.paginate(stmt, page=page, per_page=per_page)


def audit_log_repo(db: Session) -> AuditLogRepository:
    return AuditLogRepository(db)
