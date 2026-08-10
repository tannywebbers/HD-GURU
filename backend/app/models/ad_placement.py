from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONType, TimestampMixin, generate_uuid


class AdPlacement(Base, TimestampMixin):
    """A named area in the UI (landing_top, countdown_bottom, …) that can
    render one or more ad slots. Placements never block page flow — an empty
    or failed placement simply renders nothing.
    """

    __tablename__ = "ad_placements"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    name: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    responsive: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # lazy = load near viewport, eager = load immediately on mount.
    behavior: Mapped[str] = mapped_column(String(32), default="lazy", nullable=False)

    slots: Mapped[list["AdPlacementProvider"]] = relationship(
        back_populates="placement",
        cascade="all, delete-orphan",
        order_by="AdPlacementProvider.priority",
        lazy="selectin",
    )


class AdPlacementProvider(Base, TimestampMixin):
    """Association between a placement and a provider, carrying the priority,
    frequency and per-placement overrides. Priority picks which provider is
    used when several are configured for the same placement.
    """

    __tablename__ = "ad_placement_providers"
    __table_args__ = (
        UniqueConstraint(
            "placement_id", "provider_id", name="uq_ad_placement_provider"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    placement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ad_placements.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ad_providers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    frequency: Mapped[str] = mapped_column(
        String(32), default="every_page", nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config: Mapped[Any] = mapped_column(JSONType, default=dict, nullable=False)

    placement: Mapped[AdPlacement] = relationship(back_populates="slots")
    provider = relationship("AdProvider")
