from __future__ import annotations

import datetime as dt

from app.core.logging import log
from app.repositories.system_log import SystemLogRepository

_ALLOWED_LEVELS = {"debug", "info", "warning", "error", "critical"}


def _normalise_context(context: dict) -> dict:
    """Keep persisted context JSON-safe and bounded."""
    if not isinstance(context, dict):
        return {"value": str(context)}
    # Drop values that would not survive JSON round-tripping.
    safe: dict = {}
    for key, value in context.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
        else:
            safe[key] = str(value)
    return safe


def record_event(
    *,
    level: str,
    message: str,
    logger_name: str | None = None,
    context: dict | None = None,
) -> None:
    """Persist a structured system log entry.

    Opens its own session so it is safe to call from anywhere (workers,
    exception handlers, services). Persistence failures are swallowed so a
    broken database never takes down request handling.
    """
    if level not in _ALLOWED_LEVELS:
        level = "info"
    try:
        from app.core.database import SessionLocal

        with SessionLocal() as db:
            SystemLogRepository(db).record(
                level=level,
                message=message,
                logger_name=logger_name,
                context=_normalise_context(context or {}),
            )
            db.commit()
    except Exception as exc:  # pragma: no cover - defensive path
        log.warning("system_log_persist_failed", error=str(exc))


def record_error(
    *, message: str, logger_name: str | None = None, context: dict | None = None
) -> None:
    record_event(
        level="error",
        message=message,
        logger_name=logger_name,
        context=context,
    )


def record_warning(
    *, message: str, logger_name: str | None = None, context: dict | None = None
) -> None:
    record_event(
        level="warning",
        message=message,
        logger_name=logger_name,
        context=context,
    )


def record_worker_status(
    *, worker: str, status: str, context: dict | None = None
) -> None:
    record_event(
        level="info",
        message=f"worker {status}",
        logger_name="worker",
        context={"worker": worker, "status": status, **(context or {})},
    )
