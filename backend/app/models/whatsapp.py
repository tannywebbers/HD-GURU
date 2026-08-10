from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONType, TimestampMixin, generate_uuid
from app.models.enums import (
    WhatsAppDeliveryStatus,
    WhatsAppEventStatus,
    WhatsAppMessageDirection,
    WhatsAppMessageStatus,
)


class WhatsappContact(Base, TimestampMixin):
    __tablename__ = "whatsapp_contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    wa_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    phone_number: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    first_seen: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_seen: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    profile: Mapped[Any | None] = mapped_column(JSONType)

    messages = relationship("WhatsappMessage", back_populates="contact")


class WhatsappMessage(Base, TimestampMixin):
    __tablename__ = "whatsapp_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    # Meta's message id — the idempotency key. Never process twice.
    meta_message_id: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, nullable=False
    )
    direction: Mapped[WhatsAppMessageDirection] = mapped_column(
        Enum(WhatsAppMessageDirection, name="whatsapp_message_direction"),
        nullable=False,
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("whatsapp_contacts.id", ondelete="SET NULL"), index=True
    )
    message_type: Mapped[str] = mapped_column(
        String(32), default="unknown", nullable=False
    )
    text: Mapped[str | None] = mapped_column(Text)
    media_public_id: Mapped[str | None] = mapped_column(String(16), index=True)
    status: Mapped[WhatsAppMessageStatus] = mapped_column(
        Enum(WhatsAppMessageStatus, name="whatsapp_message_status"),
        default=WhatsAppMessageStatus.RECEIVED,
        nullable=False,
        index=True,
    )
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    meta: Mapped[Any | None] = mapped_column(JSONType)

    contact = relationship("WhatsappContact", back_populates="messages")
    delivery_statuses = relationship(
        "WhatsappMessageStatus",
        back_populates="message",
        cascade="all, delete-orphan",
    )


class WhatsappMessageStatus(Base, TimestampMixin):
    __tablename__ = "whatsapp_message_statuses"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("whatsapp_messages.id", ondelete="CASCADE"), index=True
    )
    meta_message_id: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[WhatsAppDeliveryStatus] = mapped_column(
        Enum(WhatsAppDeliveryStatus, name="whatsapp_delivery_status"),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    meta: Mapped[Any | None] = mapped_column(JSONType)

    message = relationship("WhatsappMessage", back_populates="delivery_statuses")


class WhatsappWebhookEvent(Base, TimestampMixin):
    __tablename__ = "whatsapp_webhook_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    object: Mapped[str | None] = mapped_column(String(128))
    entry_id: Mapped[str | None] = mapped_column(String(128))
    event_type: Mapped[str] = mapped_column(
        String(32), default="unknown", nullable=False
    )
    status: Mapped[WhatsAppEventStatus] = mapped_column(
        Enum(WhatsAppEventStatus, name="whatsapp_event_status"),
        default=WhatsAppEventStatus.RECEIVED,
        nullable=False,
        index=True,
    )
    payload: Mapped[Any | None] = mapped_column(JSONType)
    error: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    processed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
