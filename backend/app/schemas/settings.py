from __future__ import annotations

import datetime as dt
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class SettingItem(ORMModel):
    key: str
    group: str
    value: Any
    description: str | None
    is_secret: bool
    updated_at: dt.datetime


class SettingsOut(ORMModel):
    settings: list[SettingItem]


class SettingsItemUpdate(BaseModel):
    key: str = Field(..., min_length=1, max_length=128)
    value: Any


class SettingsUpdateRequest(BaseModel):
    settings: list[SettingsItemUpdate] = Field(..., min_length=1)


class PublicBrandingOut(ORMModel):
    """Safe, public branding values consumed by the public frontend + PWA.

    Only non-secret settings are exposed. If branding has not been configured
    the values fall back to sensible HD Guru defaults, so the public app and
    manifest never break.
    """

    app_name: str
    app_description: str
    app_logo_url: str | None = None
    app_theme_color: str | None = None
    app_primary_color: str | None = None
