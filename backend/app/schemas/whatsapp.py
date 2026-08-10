from __future__ import annotations

from pydantic import BaseModel, Field


class WhatsAppConfigUpdate(BaseModel):
    """Admin update payload. ``None`` fields are left unchanged."""

    enabled: bool | None = None
    phone_number_id: str | None = Field(default=None, max_length=128)
    phone_number: str | None = Field(default=None, max_length=32)
    business_account_id: str | None = Field(default=None, max_length=128)
    access_token: str | None = Field(default=None, max_length=512)
    verify_token: str | None = Field(default=None, max_length=255)
    app_secret: str | None = Field(default=None, max_length=255)
    api_version: str | None = Field(default=None, max_length=32)
    graph_api_base_url: str | None = Field(default=None, max_length=255)
