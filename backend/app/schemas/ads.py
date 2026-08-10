from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


# --- public ingestion -------------------------------------------------------


class AnalyticsEventIn(BaseModel):
    event: str = Field(..., min_length=1, max_length=64)
    session_id: str | None = Field(default=None, max_length=64)
    page: str | None = Field(default=None, max_length=256)
    referrer: str | None = Field(default=None, max_length=512)
    upload_id: uuid.UUID | None = None
    props: dict[str, Any] | None = None


class AdEventIn(BaseModel):
    event_type: str = Field(..., pattern="^(impression|click|load_failure)$")
    placement: str = Field(..., min_length=1, max_length=64)
    page: str | None = Field(default=None, max_length=256)
    session_id: str | None = Field(default=None, max_length=64)
    provider_id: uuid.UUID | None = None


class IngestResult(BaseModel):
    ok: bool = True


# --- admin: providers -------------------------------------------------------


class AdProviderBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    provider_type: str = Field(
        default="script",
        pattern="^(script|iframe|html|javascript|native|banner|custom)$",
    )
    base_url: str | None = Field(default=None, max_length=512)
    publisher_id: str | None = Field(default=None, max_length=255)
    zone_id: str | None = Field(default=None, max_length=255)
    site_id: str | None = Field(default=None, max_length=255)
    placement_config: dict[str, Any] | None = None
    custom_script: str | None = None
    click_through_url: str | None = Field(default=None, max_length=512)
    enabled: bool = False


class AdProviderCreate(AdProviderBase):
    pass


class AdProviderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    provider_type: str | None = Field(
        default=None,
        pattern="^(script|iframe|html|javascript|native|banner|custom)$",
    )
    base_url: str | None = Field(default=None, max_length=512)
    publisher_id: str | None = Field(default=None, max_length=255)
    zone_id: str | None = Field(default=None, max_length=255)
    site_id: str | None = Field(default=None, max_length=255)
    placement_config: dict[str, Any] | None = None
    custom_script: str | None = None
    click_through_url: str | None = Field(default=None, max_length=512)
    enabled: bool | None = None


class AdProviderItem(BaseModel):
    id: uuid.UUID
    name: str
    provider_type: str
    base_url: str | None = None
    publisher_id: str | None = None
    zone_id: str | None = None
    site_id: str | None = None
    placement_config: dict[str, Any] = {}
    custom_script: str | None = None
    click_through_url: str | None = None
    enabled: bool
    created_at: Any = None
    updated_at: Any = None


# --- admin: placements ------------------------------------------------------


class AdSlotIn(BaseModel):
    provider_id: uuid.UUID
    priority: int = Field(default=1, ge=1, le=100)
    frequency: str = Field(
        default="every_page",
        pattern="^(every_page|every_session|once_per_session|interval)$",
    )
    enabled: bool = True
    config: dict[str, Any] | None = None


class AdPlacementCreate(BaseModel):
    name: str = Field(..., pattern="^[a-z0-9_]+$", max_length=64)
    label: str = Field(..., min_length=1, max_length=128)
    enabled: bool = True
    width: int | None = Field(default=None, ge=1, le=5000)
    height: int | None = Field(default=None, ge=1, le=5000)
    responsive: bool = True
    behavior: str = Field(default="lazy", pattern="^(lazy|eager)$")
    slots: list[AdSlotIn] = Field(default_factory=list)


class AdPlacementUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=128)
    enabled: bool | None = None
    width: int | None = Field(default=None, ge=1, le=5000)
    height: int | None = Field(default=None, ge=1, le=5000)
    responsive: bool | None = None
    behavior: str | None = Field(default=None, pattern="^(lazy|eager)$")


class AdSlotItem(BaseModel):
    id: uuid.UUID
    provider_id: uuid.UUID
    provider_name: str
    provider_enabled: bool
    priority: int
    frequency: str
    enabled: bool
    config: dict[str, Any] = {}


class AdPlacementItem(BaseModel):
    id: uuid.UUID
    name: str
    label: str
    enabled: bool
    width: int | None = None
    height: int | None = None
    responsive: bool
    behavior: str
    slots: list[AdSlotItem] = Field(default_factory=list)
    created_at: Any = None
    updated_at: Any = None


class AdPlacementReorder(BaseModel):
    """New provider order for a placement (first item = highest priority)."""

    provider_ids: list[uuid.UUID] = Field(..., min_length=1)
