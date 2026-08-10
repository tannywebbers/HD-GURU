from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import log
from app.core.security import hash_password
from app.models.ad_placement import AdPlacement
from app.models.ad_provider import AdProvider
from app.models.enums import UserRole
from app.models.setting import Setting
from app.models.user import User
from app.models.watermark import Watermark


def _default_settings() -> list[dict]:
    return [
        {
            "key": "app.name",
            "value": settings.APP_NAME,
            "group": "general",
            "description": "Application display name shown on the public site and PWA manifest.",
            "is_secret": False,
        },
        {
            "key": "app.description",
            "value": (
                "Transform your photos and videos into stunning HD quality in "
                "seconds. Free, private, and delivered straight to WhatsApp."
            ),
            "group": "general",
            "description": "Tagline / meta description shown on the public site.",
            "is_secret": False,
        },
        {
            "key": "app.logo_url",
            "value": "",
            "group": "general",
            "description": "Optional public logo URL (https). Leave empty for the built-in logo.",
            "is_secret": False,
        },
        {
            "key": "app.theme_color",
            "value": "",
            "group": "general",
            "description": "Optional theme colour (hex, e.g. #05050a) used by the PWA browser UI.",
            "is_secret": False,
        },
        {
            "key": "app.primary_color",
            "value": "",
            "group": "general",
            "description": "Optional brand primary colour (hex) used by public components.",
            "is_secret": False,
        },
        {
            "key": "upload.max_upload_count",
            "value": settings.MAX_UPLOAD_COUNT,
            "group": "uploads",
            "description": "Maximum number of files per upload.",
            "is_secret": False,
        },
        {
            "key": "upload.max_file_size_mb",
            "value": settings.MAX_FILE_SIZE_MB,
            "group": "uploads",
            "description": "Maximum size of a single file in MB.",
            "is_secret": False,
        },
        {
            "key": "upload.max_upload_size_mb",
            "value": settings.MAX_UPLOAD_SIZE_MB,
            "group": "uploads",
            "description": "Maximum total upload size in MB.",
            "is_secret": False,
        },
        {
            "key": "upload.ttl_hours",
            "value": settings.DEFAULT_UPLOAD_TTL_HOURS,
            "group": "uploads",
            "description": "Default time-to-live for uploads in hours.",
            "is_secret": False,
        },
        {
            "key": "upload.allowed_mime_types",
            "value": settings.allowed_mime_types,
            "group": "uploads",
            "description": "Allowed media MIME types.",
            "is_secret": False,
        },
        {
            "key": "rate_limit.enabled",
            "value": settings.RATE_LIMIT_ENABLED,
            "group": "rate_limit",
            "description": "Global rate limiting toggle.",
            "is_secret": False,
        },
        {
            "key": "ads.enabled",
            "value": settings.ADS_ENABLED,
            "group": "ads",
            "description": "Master switch for serving advertisements.",
            "is_secret": False,
        },
        {
            "key": "ads.default_provider",
            "value": settings.ADS_DEFAULT_PROVIDER,
            "group": "ads",
            "description": "Provider used when a placement has no explicit provider.",
            "is_secret": False,
        },
        {
            "key": "ads.default_placement_behavior",
            "value": settings.ADS_DEFAULT_PLACEMENT_BEHAVIOR,
            "group": "ads",
            "description": "lazy (load near viewport) or eager (load on mount).",
            "is_secret": False,
        },
        {
            "key": "analytics.enabled",
            "value": settings.ANALYTICS_ENABLED,
            "group": "analytics",
            "description": "Master switch for traffic analytics tracking.",
            "is_secret": False,
        },
        {
            "key": "analytics.retention_days",
            "value": settings.ANALYTICS_RETENTION_DAYS,
            "group": "analytics",
            "description": "Days raw analytics/ad events are kept before purging.",
            "is_secret": False,
        },
    ]


def seed_default_settings(db: Session) -> None:
    """Insert default settings, backfilling any keys added after first run."""
    existing_keys = set(db.scalars(select(Setting.key)))
    added = 0
    for item in _default_settings():
        if item["key"] not in existing_keys:
            db.add(Setting(**item))
            added += 1
    if added:
        db.commit()
        log.info("seeded default settings", added=added)


def seed_admin(db: Session) -> None:
    email = settings.SEED_ADMIN_EMAIL.strip().lower()
    password = settings.SEED_ADMIN_PASSWORD
    if not email or not password:
        return
    if db.scalar(select(User).where(User.email == email)):
        return
    db.add(
        User(
            email=email,
            password_hash=hash_password(password),
            full_name="Seed Admin",
            role=UserRole.ADMIN,
            is_active=True,
            must_change_password=True,
        )
    )
    db.commit()
    log.info("seeded admin user", email=email)


def seed_default_watermark(db: Session) -> None:
    """Seed a sensible text watermark when none exists and watermarks are enabled."""
    if not settings.WATERMARK_ENABLED:
        return
    existing = db.scalar(select(func.count()).select_from(Watermark))
    if existing and existing > 0:
        return
    db.add(
        Watermark(
            name="default",
            type="text",
            text="HD Guru",
            position="bottom-right",
            opacity=0.35,
            size_percent=8.0,
            enabled=True,
        )
    )
    db.commit()
    log.info("seeded default watermark")


#: Providers made available out of the box. All are disabled until an admin
#: fills in real identifiers and enables them — nothing is served by default.
_PROVIDER_CATALOG = (
    ("Google AdSense", "script"),
    ("Adsterra", "script"),
    ("PropellerAds", "script"),
    ("Monetag", "script"),
    ("Media.net", "script"),
    ("Ezoic", "script"),
    ("Setupad", "script"),
    ("HilltopAds", "script"),
    ("RevContent", "native"),
    ("Taboola", "native"),
)

#: Default placement areas the public flow supports.
_PLACEMENT_CATALOG = (
    ("landing_top", "Landing top"),
    ("landing_middle", "Landing middle"),
    ("landing_bottom", "Landing bottom"),
    ("upload_bottom", "Upload bottom"),
    ("processing_bottom", "Processing bottom"),
    ("countdown_top", "Countdown top"),
    ("countdown_bottom", "Countdown bottom"),
    ("result_top", "Result top"),
    ("result_bottom", "Result bottom"),
    ("footer", "Footer"),
)


def seed_ads(db: Session) -> None:
    """Seed the provider catalog and default placement areas once."""
    existing = db.scalar(select(func.count()).select_from(AdProvider))
    if not existing:
        for name, provider_type in _PROVIDER_CATALOG:
            db.add(
                AdProvider(
                    name=name,
                    provider_type=provider_type,
                    enabled=False,
                )
            )
        log.info("seeded ad providers", count=len(_PROVIDER_CATALOG))
    existing_placements = db.scalar(select(func.count()).select_from(AdPlacement))
    if not existing_placements:
        for name, label in _PLACEMENT_CATALOG:
            db.add(
                AdPlacement(
                    name=name,
                    label=label,
                    enabled=True,
                    responsive=True,
                    behavior="lazy",
                )
            )
        log.info("seeded ad placements", count=len(_PLACEMENT_CATALOG))
    db.commit()


def run_startup_seeds() -> None:
    from app.core.database import SessionLocal

    try:
        with SessionLocal() as db:
            seed_default_settings(db)
            seed_admin(db)
            seed_default_watermark(db)
            seed_ads(db)
    except Exception:
        log.exception("startup seeding skipped (database unavailable?)")

    _run_startup_cleanup()


def _run_startup_cleanup() -> None:
    """Delete already-expired uploads once at startup (best-effort).

    Never blocks or fails application startup; the periodic beat task does the
    real work on an interval.
    """
    try:
        from app.core.database import SessionLocal
        from app.services.cleanup_service import run_expiry_cleanup

        with SessionLocal() as db:
            result = run_expiry_cleanup(db)
        if result.get("uploads_deleted"):
            log.info("startup expiry cleanup", **result)
    except Exception:
        log.exception("startup expiry cleanup skipped")
