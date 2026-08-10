from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JSONType, generate_uuid


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True)
    actor_type: Mapped[str] = mapped_column(
        String(32), default="system", nullable=False
    )  # user | api_key | system
    action: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(64))
    resource_id: Mapped[str | None] = mapped_column(String(128))
    details: Mapped[Any] = mapped_column(JSONType, default=dict, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    result: Mapped[str] = mapped_column(
        String(16), default="success", nullable=False
    )  # success | failure
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
        index=True,
    )
