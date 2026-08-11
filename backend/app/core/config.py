from __future__ import annotations

from typing import List

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "HD Guru"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    # Fraction of uptime seconds before startup we consider "ready".
    # (kept simple: the app is ready as soon as lifespan completes)

    # Database / Redis / Celery
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_TASK_ALWAYS_EAGER: bool = False
    CELERY_TASK_EAGER_PROPAGATES: bool = False
    # Max seconds a single processing task may run before being revoked.
    WORKER_TASK_TIMEOUT: int = 3600
    # Name used to identify this worker's heartbeat records.
    WORKER_NAME: str = "worker@default"
    # Seconds allowed between heartbeats before a worker is marked offline.
    WORKER_HEARTBEAT_TIMEOUT: int = 120

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "hd-guru-api"
    JWT_AUDIENCE: str = "hd-guru-client"

    # Account security
    PASSWORD_MIN_LENGTH: int = 8
    FAILED_LOGIN_MAX_ATTEMPTS: int = 5
    ACCOUNT_LOCK_MINUTES: int = 15
    EMAIL_VERIFICATION_REQUIRED: bool = False
    EMAIL_VERIFICATION_TOKEN_HOURS: int = 24
    PASSWORD_RESET_TOKEN_HOURS: int = 1
    PASSWORD_RESET_MAX_USES: int = 1

    # --- Email delivery (password reset / verification links) -----------------
    # EMAIL_BACKEND: "smtp" sends via SMTP; "console" prints the message to the
    # log. The console backend is a development fallback ONLY - the backend
    # refuses to use it in a production environment so the reset token is never
    # written to production logs.
    EMAIL_ENABLED: bool = False
    EMAIL_BACKEND: str = "console"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = ""
    # Base URL of the password-reset page on the frontend, e.g.
    #   https://hdguru.vercel.app/reset-password
    # The raw token is appended as a query parameter (never returned by the API).
    PASSWORD_RESET_URL: str = ""

    # CORS / Trusted hosts
    CORS_ORIGINS: str = "*"
    ALLOWED_HOSTS: str = "*"

    # Security hardening
    CSRF_PROTECTION_ENABLED: bool = True
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = "lax"
    COOKIE_NAME_ACCESS: str = "hdguru_access"
    COOKIE_NAME_REFRESH: str = "hdguru_refresh"
    HSTS_MAX_AGE: int = 31536000

    # Upload rules
    STORAGE_DRIVER: str = "local"
    STORAGE_DIR: str = "./storage"

    # --- S3-compatible storage (Cloudflare R2 / AWS S3 / MinIO) --------------
    # Credentials are never logged or returned to clients.
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = ""
    S3_REGION: str = "auto"
    # Optional public URL prefix when the bucket is public (e.g. the R2.dev or
    # custom-domain URL). Used only when MEDIA_URL_MODE=public.
    S3_PUBLIC_BASE_URL: str = ""
    S3_FORCE_PATH_STYLE: bool = False

    # How processed media URLs are handed to clients.
    #   "public" -> direct public URL via S3_PUBLIC_BASE_URL
    #   "signed" -> short-lived pre-signed URL
    # Local storage always falls back to the app's own /file route.
    MEDIA_URL_MODE: str = "public"
    MEDIA_SIGNED_URL_EXPIRES: int = 3600

    # --- WhatsApp Business Cloud API -------------------------------------------
    # Master toggle; when disabled the webhook still verifies signatures but
    # messages are acknowledged without being processed.
    WHATSAPP_ENABLED: bool = False
    # System-user access token (never logged, never returned to clients).
    WHATSAPP_ACCESS_TOKEN: str = ""
    # Meta API entity id for the phone number that sends/receives messages.
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    # Business display number in E.164 used to build wa.me click-to-chat links.
    WHATSAPP_PHONE_NUMBER: str = ""
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = ""
    # Webhook verification token (configured on the Meta developer portal).
    WHATSAPP_VERIFY_TOKEN: str = ""
    # App secret used to verify X-Hub-Signature-256 on webhook calls.
    WHATSAPP_APP_SECRET: str = ""
    # Graph API version is configurable so upgrades don't require code changes.
    WHATSAPP_GRAPH_API_VERSION: str = "v22.0"
    WHATSAPP_GRAPH_API_BASE_URL: str = "https://graph.facebook.com"
    # Outbound send budget (per process). Meta enforces its own per-tier limits;
    # this is a conservative local guard against uncontrolled send loops.
    WHATSAPP_MAX_SENDS_PER_MINUTE: int = 100
    WHATSAPP_SEND_TIMEOUT_SECONDS: int = 30
    # Public base URL of this backend (https://api.example.com). Used to build
    # media URLs for Meta when media is served by the app's own /file route.
    APP_PUBLIC_BASE_URL: str = ""

    DEFAULT_UPLOAD_TTL_HOURS: int = 24
    MAX_UPLOAD_COUNT: int = 5
    MAX_UPLOAD_FILES: int = 5
    MAX_FILE_SIZE_MB: int = 100
    MAX_UPLOAD_SIZE_MB: int = 500
    ALLOWED_MIME_TYPES: str = (
        "image/jpeg,image/png,image/webp,image/gif,image/bmp,image/tiff,"
        "image/heic,image/heif,"
        "video/mp4,video/quicktime,video/x-m4v,video/webm,video/x-msvideo,"
        "video/x-matroska"
    )
    ALLOWED_EXTENSIONS: str = (
        "jpg,jpeg,png,webp,gif,bmp,tiff,tif,heic,heif,"
        "mp4,mov,m4v,webm,avi,mkv"
    )

    # --- Media processing pipeline --------------------------------------------
    # Maximum input size (MB) for a single image / video. Files above the generic
    # MAX_FILE_SIZE_MB are already rejected during upload; these allow tighter
    # per-format limits.
    MAX_IMAGE_SIZE_MB: int = 50
    MAX_VIDEO_SIZE_MB: int = 100
    # Target maximum output size (MB) after processing (WhatsApp-friendly).
    MAX_IMAGE_OUTPUT_SIZE_MB: int = 5
    MAX_VIDEO_OUTPUT_SIZE_MB: int = 16
    # Longest image edge after processing.
    MAX_IMAGE_OUTPUT_DIMENSION: int = 2048
    # Video dimension caps (portrait/landscape/square are derived from these).
    MAX_VIDEO_WIDTH: int = 1920
    MAX_VIDEO_HEIGHT: int = 1080
    # Video quality floor: the highest CRF (worse quality) we are willing to use
    # while re-encoding to hit the size target. Lower = better quality.
    MIN_VIDEO_QUALITY: int = 28
    # How long processed media stays downloadable (days) before expiry cleanup.
    MEDIA_EXPIRATION_DAYS: int = 3
    # Master toggle for applying the active DB watermark. Fallback for the
    # `watermark.enabled` Setting row; that DB value is the live source of
    # truth. Defaults to False to preserve the previous production behaviour
    # (Render previously forced WATERMARK_ENABLED=false).
    WATERMARK_ENABLED: bool = False

    # --- Advertising & analytics ---------------------------------------------
    # Master toggles and defaults. The persisted Setting rows (ads.* / analytics.*)
    # can be changed from the admin dashboard without redeploying.
    ADS_ENABLED: bool = False
    # Default provider name used by placements that have no explicit provider.
    ADS_DEFAULT_PROVIDER: str = ""
    # Lazy defers loading until the slot is near the viewport; eager loads at mount.
    ADS_DEFAULT_PLACEMENT_BEHAVIOR: str = "lazy"
    ANALYTICS_ENABLED: bool = True
    # Raw analytics/ad event rows are purged after this many days. Aggregated
    # daily stats are kept indefinitely.
    ANALYTICS_RETENTION_DAYS: int = 90
    # Ingest budget per client (by hashed IP) to stop fake analytics floods.
    ANALYTICS_EVENTS_PER_MINUTE: int = 120
    AD_EVENTS_PER_MINUTE: int = 60

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT_PER_MINUTE: int = 60
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 10
    RATE_LIMIT_UPLOAD_PER_MINUTE: int = 20

    # Seed admin (optional)
    SEED_ADMIN_EMAIL: str = ""
    SEED_ADMIN_PASSWORD: str = ""

    # --- validation ---------------------------------------------------------
    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be at least 32 characters long."
            )
        return value

    @field_validator("MAX_UPLOAD_COUNT", "MAX_UPLOAD_FILES")
    @classmethod
    def validate_upload_count(cls, value: int) -> int:
        if value < 1 or value > 10:
            raise ValueError("MAX_UPLOAD_COUNT/MAX_UPLOAD_FILES must be between 1 and 10.")
        return value

    @field_validator(
        "MAX_FILE_SIZE_MB",
        "MAX_UPLOAD_SIZE_MB",
        "MAX_IMAGE_SIZE_MB",
        "MAX_VIDEO_SIZE_MB",
        "MAX_IMAGE_OUTPUT_SIZE_MB",
        "MAX_VIDEO_OUTPUT_SIZE_MB",
        "MAX_IMAGE_OUTPUT_DIMENSION",
        "MAX_VIDEO_WIDTH",
        "MAX_VIDEO_HEIGHT",
        "MIN_VIDEO_QUALITY",
        "MEDIA_EXPIRATION_DAYS",
    )
    @classmethod
    def validate_positive_size(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Sizes and dimensions must be greater than zero.")
        return value

    @field_validator("ANALYTICS_RETENTION_DAYS")
    @classmethod
    def validate_retention(cls, value: int) -> int:
        if value < 1 or value > 3650:
            raise ValueError("ANALYTICS_RETENTION_DAYS must be between 1 and 3650.")
        return value

    @field_validator("ANALYTICS_EVENTS_PER_MINUTE", "AD_EVENTS_PER_MINUTE")
    @classmethod
    def validate_event_limits(cls, value: int) -> int:
        if value < 1 or value > 100000:
            raise ValueError("Analytics event limits must be between 1 and 100000.")
        return value

    @field_validator(
        "ALLOWED_MIME_TYPES", "ALLOWED_EXTENSIONS", "CORS_ORIGINS", "ALLOWED_HOSTS"
    )
    @classmethod
    def validate_csv_non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("CSV settings must not be empty.")
        return value

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value:
            raise ValueError("DATABASE_URL is required.")
        return value

    @field_validator("PASSWORD_MIN_LENGTH")
    @classmethod
    def validate_password_min_length(cls, value: int) -> int:
        if value < 8:
            raise ValueError("PASSWORD_MIN_LENGTH must be at least 8.")
        return value

    @field_validator("FAILED_LOGIN_MAX_ATTEMPTS", "ACCOUNT_LOCK_MINUTES")
    @classmethod
    def validate_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Lock settings must be greater than zero.")
        return value

    @field_validator("STORAGE_DRIVER")
    @classmethod
    def validate_storage_driver(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"local", "s3"}:
            raise ValueError("STORAGE_DRIVER must be 'local' or 's3'.")
        return value

    @field_validator("MEDIA_URL_MODE")
    @classmethod
    def validate_media_url_mode(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"public", "signed"}:
            raise ValueError("MEDIA_URL_MODE must be 'public' or 'signed'.")
        return value

    @field_validator("MEDIA_SIGNED_URL_EXPIRES")
    @classmethod
    def validate_expiry_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Expiry values must be greater than zero.")
        return value

    @field_validator("WHATSAPP_GRAPH_API_VERSION")
    @classmethod
    def validate_whatsapp_api_version(cls, value: str) -> str:
        value = value.strip().lstrip("/")
        if not value.lower().startswith("v") or not value[1:].replace(".", "").isdigit():
            raise ValueError(
                "WHATSAPP_GRAPH_API_VERSION must look like 'v20.0'."
            )
        return value

    @field_validator("WHATSAPP_PHONE_NUMBER")
    @classmethod
    def validate_whatsapp_phone_number(cls, value: str) -> str:
        value = value.strip()
        digits = "".join(ch for ch in value if ch.isdigit())
        if value and (not value.startswith("+") or not 10 <= len(digits) <= 15):
            raise ValueError(
                "WHATSAPP_PHONE_NUMBER must be an E.164 number with a leading '+', "
                "e.g. +15550123456."
            )
        return value

    @field_validator("WHATSAPP_MAX_SENDS_PER_MINUTE", "WHATSAPP_SEND_TIMEOUT_SECONDS")
    @classmethod
    def validate_whatsapp_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("WhatsApp limits must be greater than zero.")
        return value

    @model_validator(mode="after")
    def validate_s3_settings(self) -> "Settings":
        if self.STORAGE_DRIVER != "s3":
            return self
        missing = [
            name
            for name, value in {
                "S3_ENDPOINT_URL": self.S3_ENDPOINT_URL,
                "S3_ACCESS_KEY_ID": self.S3_ACCESS_KEY_ID,
                "S3_SECRET_ACCESS_KEY": self.S3_SECRET_ACCESS_KEY,
                "S3_BUCKET_NAME": self.S3_BUCKET_NAME,
            }.items()
            if not value.strip()
        ]
        if missing:
            raise ValueError(
                "STORAGE_DRIVER=s3 requires "
                + ", ".join(missing)
                + " to be set."
            )
        return self

    @field_validator("COOKIE_SAMESITE")
    @classmethod
    def validate_samesite(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"lax", "strict", "none"}:
            raise ValueError("COOKIE_SAMESITE must be lax, strict or none.")
        return value

    @field_validator("EMAIL_BACKEND")
    @classmethod
    def validate_email_backend(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"smtp", "console"}:
            raise ValueError("EMAIL_BACKEND must be 'smtp' or 'console'.")
        return value

    @field_validator("SMTP_PORT")
    @classmethod
    def validate_smtp_port(cls, value: int) -> int:
        if value <= 0 or value > 65535:
            raise ValueError("SMTP_PORT must be a valid port (1-65535).")
        return value

    @field_validator("PASSWORD_RESET_URL")
    @classmethod
    def validate_password_reset_url(cls, value: str) -> str:
        value = value.strip()
        if value and not value.startswith(("http://", "https://")):
            raise ValueError(
                "PASSWORD_RESET_URL must be an absolute http(s) URL."
            )
        return value

    @field_validator("WORKER_TASK_TIMEOUT", "WORKER_HEARTBEAT_TIMEOUT")
    @classmethod
    def validate_timeout_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Worker timeouts must be greater than zero.")
        return value

    # --- derived helpers -----------------------------------------------------
    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def allowed_hosts_list(self) -> List[str]:
        return [h.strip() for h in self.ALLOWED_HOSTS.split(",") if h.strip()]

    @property
    def allowed_mime_types(self) -> List[str]:
        return [
            m.strip().lower()
            for m in self.ALLOWED_MIME_TYPES.split(",")
            if m.strip()
        ]

    @property
    def allowed_extensions(self) -> List[str]:
        return [
            e.strip().lower().lstrip(".")
            for e in self.ALLOWED_EXTENSIONS.split(",")
            if e.strip()
        ]

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def max_image_size_bytes(self) -> int:
        return self.MAX_IMAGE_SIZE_MB * 1024 * 1024

    @property
    def max_video_size_bytes(self) -> int:
        return self.MAX_VIDEO_SIZE_MB * 1024 * 1024

    @property
    def max_image_output_size_bytes(self) -> int:
        return self.MAX_IMAGE_OUTPUT_SIZE_MB * 1024 * 1024

    @property
    def max_video_output_size_bytes(self) -> int:
        return self.MAX_VIDEO_OUTPUT_SIZE_MB * 1024 * 1024


def get_settings() -> Settings:
    return Settings()


settings = get_settings()
