from __future__ import annotations

import uuid

from sqlalchemy import (
    BigInteger,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid
from app.models.enums import MediaStatus


class MediaFile(Base, TimestampMixin):
    __tablename__ = "media_files"
    __table_args__ = (
        UniqueConstraint(
            "upload_id", "seq", name="uq_media_files_upload_seq"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    public_id: Mapped[str] = mapped_column(
        String(16), unique=True, index=True, nullable=False
    )
    upload_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("uploads.id", ondelete="CASCADE"), index=True, nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)

    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    extension: Mapped[str] = mapped_column(String(16), nullable=False)
    file_size: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False
    )
    duration: Mapped[float | None] = mapped_column(Float)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    storage_location: Mapped[str] = mapped_column(String(1024), nullable=False)
    storage_provider: Mapped[str] = mapped_column(
        String(16), default="local", nullable=False
    )
    original_object_key: Mapped[str | None] = mapped_column(String(1024))
    download_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    whatsapp_delivery_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    status: Mapped[MediaStatus] = mapped_column(
        Enum(MediaStatus, name="media_status"),
        default=MediaStatus.QUEUED,
        nullable=False,
        index=True,
    )
    error: Mapped[str | None] = mapped_column(Text)

    upload = relationship("Upload", back_populates="media_files")
