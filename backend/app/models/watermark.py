from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, generate_uuid


class Watermark(Base, TimestampMixin):
    __tablename__ = "watermarks"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    name: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, nullable=False
    )
    type: Mapped[str] = mapped_column(
        String(16), default="text", nullable=False
    )  # text | image
    text: Mapped[str | None] = mapped_column(String(255))
    image_url: Mapped[str | None] = mapped_column(String(512))
    position: Mapped[str] = mapped_column(
        String(32), default="bottom-right", nullable=False
    )
    opacity: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    size_percent: Mapped[float] = mapped_column(
        Float, default=10.0, nullable=False
    )
    margin: Mapped[float | None] = mapped_column(Float)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
