from __future__ import annotations

import datetime as dt
import time

from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.core.logging import log
from app.core.redis import get_redis, redis_available

_STARTED_AT = time.monotonic()


def _db_ok() -> tuple[bool, str]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "ok"
    except Exception as exc:
        log.warning("health check database failed", error=str(exc))
        return False, "database unavailable"


def _redis_ok() -> tuple[bool, str]:
    if redis_available():
        return True, "ok"
    try:
        get_redis().ping()
        return True, "ok"
    except Exception as exc:
        log.warning("health check redis failed", error=str(exc))
        return False, "redis unavailable"


def _storage_ok() -> tuple[bool, str]:
    try:
        from app.core.storage import get_storage

        get_storage().check_writable()
        return True, "ok"
    except Exception as exc:
        log.warning("health check storage failed", error=str(exc))
        return False, "storage unavailable"


def _workers_ok() -> tuple[bool, str]:
    try:
        from app.workers.celery_app import celery_app

        if settings.CELERY_TASK_ALWAYS_EAGER:
            return True, "eager_mode"
        ping = celery_app.control.ping(timeout=1)
        return bool(ping), "ok" if ping else "no_workers"
    except Exception as exc:
        log.warning("health check workers failed", error=str(exc))
        return False, "workers unavailable"


def _whatsapp_ok() -> tuple[bool, str]:
    """Report WhatsApp integration state without exposing any credentials.

    WhatsApp is an optional feature: when disabled the component reports a
    healthy ``disabled`` state so it never degrades the overall status. When
    enabled, the check verifies the effective configuration (DB row overrides
    env) contains the credentials needed to send messages.
    """
    try:
        from app.core.database import SessionLocal
        from app.services.whatsapp.config import load_config

        with SessionLocal() as db:
            cfg = load_config(db)
        if not cfg.enabled:
            return True, "disabled"
        if cfg.is_fully_configured():
            return True, "configured"
        missing = [name for name, present in (
            ("access_token", bool(cfg.access_token)),
            ("phone_number_id", bool(cfg.phone_number_id)),
        ).items() if not present]
        return False, "not configured: " + ", ".join(missing)
    except Exception as exc:
        log.warning("health check whatsapp failed", error=str(exc))
        return False, "whatsapp unavailable"


def uptime_seconds() -> float:
    return time.monotonic() - _STARTED_AT


def health_payload(db_ok: tuple[bool, str] | None = None) -> dict:
    db = db_ok or _db_ok()
    redis = _redis_ok()
    storage = _storage_ok()
    workers = _workers_ok()
    whatsapp = _whatsapp_ok()
    components = {
        "application": {"status": "ok", "detail": None},
        "database": {"status": "ok" if db[0] else "unavailable", "detail": db[1]},
        "redis": {"status": "ok" if redis[0] else "unavailable", "detail": redis[1]},
        "workers": {
            "status": "ok" if workers[0] else "unavailable",
            "detail": workers[1],
        },
        "storage": {
            "status": "ok" if storage[0] else "unavailable",
            "detail": storage[1],
        },
        "whatsapp": {
            "status": "ok" if whatsapp[0] else "unavailable",
            "detail": whatsapp[1],
        },
    }
    # "disabled" (WhatsApp off) is reported as status "ok" with detail "disabled":
    # it is an optional feature, not a degraded dependency.
    overall = (
        "ok"
        if all(c["status"] == "ok" for c in components.values())
        else "degraded"
    )
    if overall == "degraded":
        log.warning(
            "health_degraded",
            database=db[1] if not db[0] else None,
            redis=redis[1] if not redis[0] else None,
            workers=workers[1] if not workers[0] else None,
            storage=storage[1] if not storage[0] else None,
            whatsapp=whatsapp[1] if not whatsapp[0] else None,
        )
    return {
        "status": overall,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": round(uptime_seconds(), 2),
        "components": components,
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
    }


def readiness_payload() -> dict:
    db = _db_ok()
    redis = _redis_ok()
    storage = _storage_ok()
    workers = _workers_ok()
    checks = {
        "database": "ok" if db[0] else "unavailable",
        "redis": "ok" if redis[0] else "unavailable",
        "workers": "ok" if workers[0] else "unavailable",
        "storage": "ok" if storage[0] else "unavailable",
    }
    ready = all(v == "ok" for v in checks.values())
    return {
        "ready": ready,
        "status": "ready" if ready else "not_ready",
        "checks": checks,
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
