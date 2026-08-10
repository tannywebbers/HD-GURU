from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONType, TimestampMixin, generate_uuid
from app.models.enums import JobStatus


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    job_type: Mapped[str] = mapped_column(
        String(128), index=True, nullable=False
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"),
        default=JobStatus.QUEUED,
        nullable=False,
        index=True,
    )
    upload_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("uploads.id", ondelete="SET NULL"), index=True
    )
    celery_task_id: Mapped[str | None] = mapped_column(
        String(128), unique=True, index=True
    )
    args: Mapped[Any] = mapped_column(JSONType, default=dict, nullable=False)
    result: Mapped[Any | None] = mapped_column(JSONType)
    retries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    traceback: Mapped[str | None] = mapped_column(Text)
    worker_id: Mapped[str | None] = mapped_column(String(128))
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    upload = relationship("Upload", back_populates="jobs")
