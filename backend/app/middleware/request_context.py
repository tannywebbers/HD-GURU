from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.services import system_log_service


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request ID, bind logging context, time the request and log it.

    Emits a structured ``request_started`` event on the way in and a
    ``request_completed`` event on the way out, and persists ERROR/CRITICAL
    events to the system log table.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        start = time.perf_counter()

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        logger = structlog.get_logger("access")
        logger.info(
            "request_started",
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.exception("request_failed", duration_ms=duration_ms)
            system_log_service.record_error(
                message="unhandled request exception",
                logger_name="access",
                context={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{duration_ms}"

        logger.info(
            "request_completed",
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response
