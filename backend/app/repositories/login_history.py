from __future__ import annotations

from sqlalchemy import select

from app.models.login_history import LoginHistory
from app.repositories.base import BaseRepository
from app.utils.pagination import Page


class LoginHistoryRepository(BaseRepository[LoginHistory]):
    model = LoginHistory

    def record(
        self,
        *,
        email: str,
        success: bool,
        user_id=None,
        failure_reason: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> LoginHistory:
        entry = LoginHistory(
            email=email,
            success=success,
            user_id=user_id,
            failure_reason=failure_reason,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(entry)
        return entry

    def list_for_user(
        self, user_id, *, page: int = 1, per_page: int = 20
    ) -> Page[LoginHistory]:
        stmt = (
            select(LoginHistory)
            .where(LoginHistory.user_id == user_id)
            .order_by(LoginHistory.created_at.desc())
        )
        return self.paginate(stmt, page=page, per_page=per_page)

    def list_recent(self, *, limit: int = 50) -> list[LoginHistory]:
        stmt = select(LoginHistory).order_by(
            LoginHistory.created_at.desc()
        ).limit(limit)
        return list(self.db.scalars(stmt))
