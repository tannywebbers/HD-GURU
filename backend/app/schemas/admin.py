from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


# --- shared ----------------------------------------------------------------


class AdminMe(ORMModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    role: str
    permissions: list[str] = Field(default_factory=list)


# --- dashboard -------------------------------------------------------------


class DashboardCounters(BaseModel):
    uploads_total: int
    uploads_today: int
    media_total: int
    media_completed: int
    downloads_total: int
    whatsapp_deliveries_total: int
    whatsapp_messages_total: int
    whatsapp_contacts_total: int
    users_total: int
    jobs_queued: int
    jobs_running: int
    jobs_failed: int
    jobs_succeeded: int
    error_logs_24h: int


class DashboardResponse(BaseModel):
    counters: DashboardCounters
    recent_uploads: list[dict[str, Any]]
    recent_jobs: list[dict[str, Any]]
    storage: dict[str, Any]
    system: dict[str, Any]
    health: dict[str, Any]


# --- media -----------------------------------------------------------------


class AdminMediaItem(ORMModel):
    id: uuid.UUID
    public_id: str
    seq: int
    original_filename: str
    mime_type: str
    extension: str
    file_size: int
    width: int | None
    height: int | None
    duration: float | None
    storage_provider: str
    status: str
    error: str | None
    download_count: int
    whatsapp_delivery_count: int
    created_at: dt.datetime
    updated_at: dt.datetime
    upload_public_id: str | None = None
    processed: dict[str, Any] | None = None


class AdminMediaPage(BaseModel):
    items: list[AdminMediaItem]
    total: int
    page: int
    per_page: int
    pages: int


# --- jobs ------------------------------------------------------------------


class AdminJobItem(ORMModel):
    id: uuid.UUID
    job_type: str
    status: str
    upload_id: uuid.UUID | None
    celery_task_id: str | None
    args: dict[str, Any]
    result: dict[str, Any] | None
    retries: int
    max_retries: int
    worker_id: str | None
    started_at: dt.datetime | None
    finished_at: dt.datetime | None
    created_at: dt.datetime
    updated_at: dt.datetime


class AdminJobPage(BaseModel):
    items: list[AdminJobItem]
    total: int
    page: int
    per_page: int
    pages: int


class JobRetryResult(BaseModel):
    job_id: uuid.UUID
    status: str
    celery_task_id: str | None


# --- users -----------------------------------------------------------------


class AdminUserItem(ORMModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    role: str
    is_active: bool
    email_verified: bool
    last_login_at: dt.datetime | None
    failed_login_count: int
    is_locked: bool
    locked_until: dt.datetime | None
    must_change_password: bool
    token_version: int
    created_at: dt.datetime
    updated_at: dt.datetime
    uploads_count: int = 0


class AdminUserPage(BaseModel):
    items: list[AdminUserItem]
    total: int
    page: int
    per_page: int
    pages: int


class UserCreateRequest(BaseModel):
    email: EmailStr = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)
    role: str = Field(default="viewer")
    is_active: bool = True
    must_change_password: bool = True


class UserUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    role: str | None = None
    is_active: bool | None = None
    must_change_password: bool | None = None
    email_verified: bool | None = None


# --- whatsapp --------------------------------------------------------------


class AdminWhatsappStats(BaseModel):
    messages_total: int
    messages_inbound: int
    messages_outbound: int
    messages_failed: int
    messages_delivered: int
    messages_read: int
    contacts_total: int
    events_total: int
    events_failed: int
    webhook: dict[str, Any]
    config: dict[str, Any]


class AdminWhatsappMessageItem(ORMModel):
    id: uuid.UUID
    meta_message_id: str
    direction: str
    message_type: str
    text: str | None
    media_public_id: str | None
    status: str
    error_code: str | None
    error_message: str | None
    timestamp: dt.datetime | None
    created_at: dt.datetime
    contact_phone: str | None = None
    contact_name: str | None = None


class AdminWhatsappMessagePage(BaseModel):
    items: list[AdminWhatsappMessageItem]
    total: int
    page: int
    per_page: int
    pages: int


class AdminWhatsappContactItem(ORMModel):
    id: uuid.UUID
    wa_id: str
    phone_number: str
    display_name: str | None
    first_seen: dt.datetime
    last_seen: dt.datetime
    created_at: dt.datetime


class AdminWhatsappContactPage(BaseModel):
    items: list[AdminWhatsappContactItem]
    total: int
    page: int
    per_page: int
    pages: int


class AdminWhatsappEventItem(ORMModel):
    id: uuid.UUID
    object: str | None
    entry_id: str | None
    event_type: str
    status: str
    error: str | None
    received_at: dt.datetime
    processed_at: dt.datetime | None
    created_at: dt.datetime


class AdminWhatsappEventPage(BaseModel):
    items: list[AdminWhatsappEventItem]
    total: int
    page: int
    per_page: int
    pages: int


# --- watermark -------------------------------------------------------------


class WatermarkIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    type: str = Field(default="text", pattern="^(text|image)$")
    text: str | None = Field(default=None, max_length=255)
    image_url: str | None = Field(default=None, max_length=512)
    position: str = Field(default="bottom-right", max_length=32)
    opacity: float = Field(default=0.35, ge=0.05, le=1.0)
    size_percent: float = Field(default=8.0, ge=1.0, le=50.0)
    margin: float | None = Field(default=None, ge=0, le=1000)
    enabled: bool = True


class WatermarkUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    type: str | None = Field(default=None, pattern="^(text|image)$")
    text: str | None = Field(default=None, max_length=255)
    image_url: str | None = Field(default=None, max_length=512)
    position: str | None = Field(default=None, max_length=32)
    opacity: float | None = Field(default=None, ge=0.05, le=1.0)
    size_percent: float | None = Field(default=None, ge=1.0, le=50.0)
    margin: float | None = Field(default=None, ge=0, le=1000)
    enabled: bool | None = None


class WatermarkOut(ORMModel):
    id: uuid.UUID
    name: str
    type: str
    text: str | None
    image_url: str | None
    position: str
    opacity: float
    size_percent: float
    margin: float | None
    enabled: bool
    created_at: dt.datetime
    updated_at: dt.datetime


# --- storage ---------------------------------------------------------------


class StorageResponse(BaseModel):
    driver: str
    provider: str
    base_path: str | None = None
    bucket: str | None = None
    endpoint: str | None = None
    region: str | None = None
    media_url_mode: str
    writable: bool
    objects: int
    used_bytes: int | None = None


# --- settings --------------------------------------------------------------


class AdminSettingItem(BaseModel):
    key: str
    group: str
    value: Any
    description: str | None
    is_secret: bool
    updated_at: dt.datetime | None


class AdminSettingsOut(BaseModel):
    settings: list[AdminSettingItem]


# --- logs & audit ----------------------------------------------------------


class AdminLogItem(ORMModel):
    id: uuid.UUID
    level: str
    logger_name: str | None
    message: str
    context: dict[str, Any]
    created_at: dt.datetime


class AdminLogPage(BaseModel):
    items: list[AdminLogItem]
    total: int
    page: int
    per_page: int
    pages: int


class AdminAuditItem(ORMModel):
    id: uuid.UUID
    actor_id: uuid.UUID | None
    actor_type: str
    action: str
    resource_type: str | None
    resource_id: str | None
    details: dict[str, Any]
    ip_address: str | None
    user_agent: str | None
    result: str
    created_at: dt.datetime


class AdminAuditPage(BaseModel):
    items: list[AdminAuditItem]
    total: int
    page: int
    per_page: int
    pages: int


# --- security --------------------------------------------------------------


class AdminLoginHistoryItem(ORMModel):
    id: uuid.UUID
    email: str
    success: bool
    failure_reason: str | None
    ip_address: str | None
    user_agent: str | None
    created_at: dt.datetime


class AdminLoginHistoryPage(BaseModel):
    items: list[AdminLoginHistoryItem]
    total: int
    page: int
    per_page: int
    pages: int


class AdminApiKeyItem(ORMModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    scopes: list[Any]
    last_used_at: dt.datetime | None
    expires_at: dt.datetime | None
    is_active: bool
    created_at: dt.datetime
    user_email: str | None = None


class SecurityOverview(BaseModel):
    users_total: int
    locked_accounts: int
    active_api_keys: int
    failed_logins_24h: int
    recent_sessions: int


# --- health ----------------------------------------------------------------


class AdminHealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    uptime_seconds: float
    components: dict[str, Any]
    timestamp: str
    workers: list[dict[str, Any]]
