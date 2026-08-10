from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from pydantic import BaseModel, Field


class AnalyticsOverview(BaseModel):
    range_days: int
    visitors: int
    page_views: int
    uploads: int
    uploads_completed: int
    get_hd_clicks: int
    whatsapp_opens: int
    whatsapp_requests: int
    media_deliveries: int
    errors: int
    processing_rate: float | None = None
    ad_impressions: int = 0
    ad_clicks: int = 0
    ad_load_failures: int = 0


class AnalyticsTimePoint(BaseModel):
    date: str
    visitors: int = 0
    page_views: int = 0
    uploads: int = 0
    get_hd_clicks: int = 0
    media_deliveries: int = 0
    errors: int = 0


class AnalyticsTimeseries(BaseModel):
    points: list[AnalyticsTimePoint]


class AnalyticsEventItem(BaseModel):
    id: uuid.UUID
    event_type: str
    session_id: str | None = None
    page: str | None = None
    device: str | None = None
    browser: str | None = None
    os: str | None = None
    country: str | None = None
    referrer_category: str | None = None
    created_at: dt.datetime


class AnalyticsEventPage(BaseModel):
    items: list[AnalyticsEventItem]
    total: int
    page: int
    per_page: int
    pages: int


class AnalyticsTopItem(BaseModel):
    key: str
    count: int


class AnalyticsTopList(BaseModel):
    items: list[AnalyticsTopItem]
