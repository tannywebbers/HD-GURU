from __future__ import annotations

import datetime as dt
import uuid

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

from app.models.base import Base, TimestampMixin, generate_uuid
from app.models.enums import UploadStatus


class Upload(Base, TimestampMixin):
    __tablename__ = "uploads"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    public_id: Mapped[str] = mapped_column(
        String(16), unique=True, index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    optimized_filename: Mapped[str | None] = mapped_column(String(512))
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    extension: Mapped[str] = mapped_column(String(16), nullable=False)
    file_size: Mapped[int] = mapped_column(
        BigInteger, default=0, nullable=False
    )
    duration: Mapped[float | None] = mapped_column(Float)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    storage_location: Mapped[str] = mapped_column(String(1024), nullable=False)

    status: Mapped[UploadStatus] = mapped_column(
        Enum(UploadStatus, name="upload_status"),
        default=UploadStatus.RECEIVED,
        nullable=False,
        index=True,
    )
    file_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    download_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    whatsapp_delivery_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    expires_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    user = relationship("User", back_populates="uploads")
    media_files = relationship(
        "MediaFile",
        back_populates="upload",
        cascade="all, delete-orphan",
        order_by="MediaFile.seq",
    )
    processed_media = relationship(
        "ProcessedMedia",
        back_populates="upload",
        cascade="all, delete-orphan",
    )
    jobs = relationship("Job", back_populates="upload")
