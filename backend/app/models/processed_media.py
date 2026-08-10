from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONType, TimestampMixin, generate_uuid
from app.models.enums import MediaStatus


class ProcessedMedia(Base, TimestampMixin):
    __tablename__ = "processed_media"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    upload_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("uploads.id", ondelete="CASCADE"), index=True, nullable=False
    )
    media_file_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_files.id", ondelete="SET NULL")
    )

    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    processed_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    extension: Mapped[str] = mapped_column(String(16), nullable=False)
    file_size: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False
    )
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    duration: Mapped[float | None] = mapped_column(Float)
    storage_location: Mapped[str] = mapped_column(String(1024), nullable=False)
    thumbnail_location: Mapped[str | None] = mapped_column(String(1024))
    storage_provider: Mapped[str] = mapped_column(
        String(16), default="local", nullable=False
    )
    processed_object_key: Mapped[str | None] = mapped_column(String(1024))
    thumbnail_object_key: Mapped[str | None] = mapped_column(String(1024))
    watermark_ref: Mapped[Any | None] = mapped_column(JSONType)
    download_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    completed_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    status: Mapped[MediaStatus] = mapped_column(
        Enum(MediaStatus, name="media_status"),
        default=MediaStatus.PENDING,
        nullable=False,
    )

    upload = relationship("Upload", back_populates="processed_media")
