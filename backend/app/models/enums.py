from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    USER = "user"
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class Permission(str, enum.Enum):
    """Fine-grained permissions enforced by the admin API.

    New capabilities (advertising, monetization, analytics…) register here so
    the dashboard can grow without redesigning the permission layer.
    """

    DASHBOARD_VIEW = "dashboard.view"
    MEDIA_VIEW = "media.view"
    MEDIA_DELETE = "media.delete"
    JOBS_VIEW = "jobs.view"
    JOBS_RETRY = "jobs.retry"
    USERS_VIEW = "users.view"
    USERS_MANAGE = "users.manage"
    WHATSAPP_VIEW = "whatsapp.view"
    WHATSAPP_MANAGE = "whatsapp.manage"
    WHATSAPP_CREDENTIALS = "whatsapp.credentials"
    WHATSAPP_TEST = "whatsapp.test"
    WATERMARK_VIEW = "watermark.view"
    WATERMARK_MANAGE = "watermark.manage"
    STORAGE_VIEW = "storage.view"
    SETTINGS_VIEW = "settings.view"
    SETTINGS_MANAGE = "settings.manage"
    SECURITY_VIEW = "security.view"
    SECURITY_MANAGE = "security.manage"
    LOGS_VIEW = "logs.view"
    AUDIT_VIEW = "audit.view"
    HEALTH_VIEW = "health.view"
    ADS_VIEW = "ads.view"
    ADS_MANAGE = "ads.manage"
    ANALYTICS_VIEW = "analytics.view"


class UploadStatus(str, enum.Enum):
    RECEIVED = "received"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MediaStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    QUEUED = "queued"
    ANALYZING = "analyzing"
    ENHANCING = "enhancing"
    WATERMARKING = "watermarking"
    COMPRESSING = "compressing"
    STORING = "storing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD = "dead"


class WorkerStatus(str, enum.Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"


class WhatsAppMessageDirection(str, enum.Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class WhatsAppMessageStatus(str, enum.Enum):
    RECEIVED = "received"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"
    IGNORED = "ignored"


class WhatsAppDeliveryStatus(str, enum.Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class WhatsAppEventStatus(str, enum.Enum):
    RECEIVED = "received"
    PROCESSED = "processed"
    FAILED = "failed"
    IGNORED = "ignored"


class AdProviderType(str, enum.Enum):
    """Integration method an ad provider uses on the client.

    ``script``/``javascript`` inject a generated snippet, ``iframe`` embeds a
    URL, ``html``/``banner``/``native`` render markup, and ``custom`` lets a
    trusted admin supply an isolated script (rendered in a sandboxed frame).
    """

    SCRIPT = "script"
    IFRAME = "iframe"
    HTML = "html"
    JAVASCRIPT = "javascript"
    NATIVE = "native"
    BANNER = "banner"
    CUSTOM = "custom"


class AdFrequency(str, enum.Enum):
    """How often a provider may render inside a placement."""

    EVERY_PAGE = "every_page"
    EVERY_SESSION = "every_session"
    ONCE_PER_SESSION = "once_per_session"
    INTERVAL = "interval"


class AdEventType(str, enum.Enum):
    IMPRESSION = "impression"
    CLICK = "click"
    LOAD_FAILURE = "load_failure"


class AnalyticsEventName(str, enum.Enum):
    """Server-known analytics event names used by the ingestion endpoint."""

    PAGE_VIEW = "page_view"
    UPLOAD_STARTED = "upload_started"
    UPLOAD_COMPLETED = "upload_completed"
    PROCESSING_STARTED = "processing_started"
    PROCESSING_COMPLETED = "processing_completed"
    GET_HD_CLICKED = "get_hd_clicked"
    WHATSAPP_OPENED = "whatsapp_opened"
    WHATSAPP_REQUEST = "whatsapp_request"
    WHATSAPP_MESSAGE_RECEIVED = "whatsapp_message_received"
    MEDIA_DELIVERED = "media_delivered"
    PROCESSING_FAILED = "processing_failed"
    UPLOAD_FAILED = "upload_failed"
