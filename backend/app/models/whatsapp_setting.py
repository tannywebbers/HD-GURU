from __future__ import annotations

import uuid

from sqlalchemy import Boolean, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, generate_uuid


class WhatsappSetting(Base, TimestampMixin):
    __tablename__ = "whatsapp_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    name: Mapped[str] = mapped_column(
        String(64), unique=True, default="primary", nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    phone_number_id: Mapped[str | None] = mapped_column(String(128))
    phone_number: Mapped[str | None] = mapped_column(String(32))
    business_account_id: Mapped[str | None] = mapped_column(String(128))
    access_token: Mapped[str | None] = mapped_column(String(512))
    webhook_verify_token: Mapped[str | None] = mapped_column(String(255))
    webhook_secret: Mapped[str | None] = mapped_column(String(255))
    graph_api_base_url: Mapped[str | None] = mapped_column(String(255))
    api_version: Mapped[str] = mapped_column(
        String(32), default="v22.0", nullable=False
    )
