from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid


class AdEvent(Base):
    """A raw ad interaction (impression / click / load failure).

    Rows are purged by the analytics retention job. Aggregates are rolled into
    ``traffic_stats`` daily counters so reporting survives the purge. Provider
    names are denormalized so reporting survives provider deletion.
    """

    __tablename__ = "ad_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    event_type: Mapped[str] = mapped_column(
        String(32), index=True, nullable=False
    )
    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ad_providers.id", ondelete="SET NULL"), index=True
    )
    placement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ad_placements.id", ondelete="SET NULL"), index=True
    )
    provider_name: Mapped[str | None] = mapped_column(String(128))
    placement_name: Mapped[str | None] = mapped_column(String(64), index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), index=True)
    page: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )
