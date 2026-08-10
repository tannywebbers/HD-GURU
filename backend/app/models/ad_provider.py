from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JSONType, TimestampMixin, generate_uuid


class AdProvider(Base, TimestampMixin):
    """An advertising network/partner the platform can serve ads from.

    Only public identifiers (publisher/zone/site IDs) plus a generated render
    snippet ever reach the client. ``api_key`` and other secrets never leave
    the server. ``custom_script`` is the explicit trusted-admin path and is
    rendered in an isolated sandboxed frame by the frontend.
    """

    __tablename__ = "ad_providers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    name: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, nullable=False
    )
    provider_type: Mapped[str] = mapped_column(
        String(32), default="script", nullable=False
    )
    base_url: Mapped[str | None] = mapped_column(String(512))
    api_key: Mapped[str | None] = mapped_column(String(512))
    publisher_id: Mapped[str | None] = mapped_column(String(255))
    zone_id: Mapped[str | None] = mapped_column(String(255))
    site_id: Mapped[str | None] = mapped_column(String(255))
    placement_config: Mapped[Any] = mapped_column(JSONType, default=dict, nullable=False)
    custom_script: Mapped[str | None] = mapped_column(Text)
    click_through_url: Mapped[str | None] = mapped_column(String(512))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
