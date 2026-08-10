from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, generate_uuid


class TrafficStat(Base):
    """Aggregated daily traffic (the long-lived analytics cube).

    One row per (date, page, device, browser, os, country, referrer category)
    combination with incrementing counters for every tracked event. This is
    the table the analytics dashboard queries; it is intentionally coarse and
    privacy-conscious (no IPs, no individual sessions).
    """

    __tablename__ = "traffic_stats"
    __table_args__ = (
        UniqueConstraint(
            "stat_date",
            "page_url",
            "device",
            "browser",
            "os",
            "country",
            "referrer",
            name="uq_traffic_stats_dims",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    stat_date: Mapped[dt.date] = mapped_column(
        Date, index=True, nullable=False
    )
    upload_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("uploads.id", ondelete="SET NULL")
    )
    ip_address: Mapped[str | None] = mapped_column(String(64))
    country: Mapped[str] = mapped_column(String(64), default="unknown", nullable=False)
    device: Mapped[str] = mapped_column(String(64), default="unknown", nullable=False)
    browser: Mapped[str] = mapped_column(String(64), default="unknown", nullable=False)
    os: Mapped[str] = mapped_column(String(64), default="unknown", nullable=False)
    page_url: Mapped[str] = mapped_column(
        String(512), default="/", nullable=False
    )
    referrer: Mapped[str] = mapped_column(
        String(64), default="direct", nullable=False
    )
    events_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    page_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sessions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    uploads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    uploads_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processing_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    get_hd_clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    whatsapp_opens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    whatsapp_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    media_deliveries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ad_impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ad_clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ad_load_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
