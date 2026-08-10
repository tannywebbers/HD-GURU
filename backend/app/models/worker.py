from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, generate_uuid
from app.models.enums import WorkerStatus


class Worker(Base, TimestampMixin):
    __tablename__ = "workers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    name: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, nullable=False
    )
    hostname: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[WorkerStatus] = mapped_column(
        Enum(WorkerStatus, name="worker_status"),
        default=WorkerStatus.OFFLINE,
        nullable=False,
    )
    current_job_id: Mapped[str | None] = mapped_column(String(128))
    last_heartbeat: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
