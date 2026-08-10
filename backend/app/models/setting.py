from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JSONType, TimestampMixin, generate_uuid


class Setting(Base, TimestampMixin):
    __tablename__ = "settings"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    key: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, nullable=False
    )
    value: Mapped[Any] = mapped_column(JSONType, nullable=False)
    group: Mapped[str] = mapped_column(
        String(64), default="general", nullable=False
    )
    description: Mapped[str | None] = mapped_column(String(512))
    is_secret: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
