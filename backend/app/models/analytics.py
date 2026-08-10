from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JSONType, generate_uuid


class Analytics(Base):
    """Raw analytics event row (the long-tail event log).

    Privacy: no raw IP addresses are stored; only coarse category labels
    (device/browser/os/country code/referrer category) plus the anonymous
    client-generated session id. Rows older than the configured retention are
    purged by the retention job; ``traffic_stats`` holds the longer-lived
    aggregates.
    """

    __tablename__ = "analytics"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    event_type: Mapped[str] = mapped_column(
        String(128), index=True, nullable=False
    )
    upload_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("uploads.id", ondelete="SET NULL"), index=True
    )
    session_id: Mapped[str | None] = mapped_column(String(64), index=True)
    page: Mapped[str | None] = mapped_column(String(128), index=True)
    device: Mapped[str | None] = mapped_column(String(32))
    browser: Mapped[str | None] = mapped_column(String(32))
    os: Mapped[str | None] = mapped_column(String(32))
    country: Mapped[str | None] = mapped_column(String(8))
    referrer_category: Mapped[str | None] = mapped_column(String(32))
    payload: Mapped[Any] = mapped_column(JSONType, default=dict, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )
