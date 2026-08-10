from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class HealthComponent(BaseModel):
    status: str
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    uptime_seconds: float
    application: HealthComponent
    database: HealthComponent
    redis: HealthComponent
    workers: HealthComponent
    storage: HealthComponent
    whatsapp: HealthComponent
    timestamp: str


class ReadinessResponse(BaseModel):
    ready: bool
    status: str
    checks: dict[str, Any]
    timestamp: str
