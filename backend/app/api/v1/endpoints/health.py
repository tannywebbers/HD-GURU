from __future__ import annotations

from fastapi import APIRouter, Response

from app.core.config import settings
from app.schemas.health import HealthResponse, ReadinessResponse
from app.services import health_service

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness / health check",
    description=(
        "Reports the status of the application, database, Redis, workers, "
        "storage and WhatsApp along with version, environment, uptime and a "
        "timestamp. Always returns HTTP 200; inspect ``status`` for degradation. "
        "WhatsApp reports ``ok`` with detail ``disabled`` when the feature is "
        "turned off."
    ),
    responses={
        200: {
            "description": "Health report (status may be ok or degraded)",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "version": settings.APP_VERSION,
                        "environment": "development",
                        "uptime_seconds": 12.5,
                        "application": {"status": "ok", "detail": None},
                        "database": {"status": "ok", "detail": None},
                        "redis": {"status": "ok", "detail": None},
                        "workers": {"status": "ok", "detail": "ok"},
                        "storage": {"status": "ok", "detail": None},
                        "whatsapp": {"status": "ok", "detail": "disabled"},
                        "timestamp": "2026-01-01T00:00:00+00:00",
                    }
                }
            },
        },
    },
)
def health() -> HealthResponse:
    payload = health_service.health_payload()
    components = payload.pop("components")
    payload.update(components)
    return HealthResponse(**payload)


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness check",
    description=(
        "Returns HTTP 200 only when every dependency is ready. When anything "
        "is unavailable the response is HTTP 503 and ``ready`` is false."
    ),
    responses={
        200: {
            "description": "All dependencies ready",
            "content": {
                "application/json": {
                    "example": {
                        "ready": True,
                        "status": "ready",
                        "checks": {
                            "database": "ok",
                            "redis": "ok",
                            "workers": "ok",
                            "storage": "ok",
                        },
                        "timestamp": "2026-01-01T00:00:00+00:00",
                    }
                }
            },
        },
        503: {
            "description": "At least one dependency is not ready",
            "content": {
                "application/json": {
                    "example": {
                        "ready": False,
                        "status": "not_ready",
                        "checks": {
                            "database": "ok",
                            "redis": "unavailable",
                            "workers": "unavailable",
                            "storage": "ok",
                        },
                        "timestamp": "2026-01-01T00:00:00+00:00",
                    }
                }
            },
        },
    },
)
def ready(response: Response) -> ReadinessResponse:
    payload = health_service.readiness_payload()
    if not payload["ready"]:
        response.status_code = 503
    return ReadinessResponse(**payload)
