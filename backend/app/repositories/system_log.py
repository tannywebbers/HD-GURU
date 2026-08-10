from __future__ import annotations

from sqlalchemy import select

from app.models.system_log import SystemLog
from app.repositories.base import BaseRepository
from app.utils.pagination import Page


class SystemLogRepository(BaseRepository[SystemLog]):
    model = SystemLog

    def record(
        self,
        *,
        level: str,
        message: str,
        logger_name: str | None = None,
        context: dict | None = None,
    ) -> SystemLog:
        entry = SystemLog(
            level=level,
            logger_name=logger_name,
            message=message,
            context=context or {},
        )
        self.db.add(entry)
        return entry

    def list_recent(
        self, *, page: int = 1, per_page: int = 20, level: str | None = None
    ) -> Page[SystemLog]:
        stmt = select(SystemLog)
        if level:
            stmt = stmt.where(SystemLog.level == level)
        stmt = stmt.order_by(SystemLog.created_at.desc())
        return self.paginate(stmt, page=page, per_page=per_page)
