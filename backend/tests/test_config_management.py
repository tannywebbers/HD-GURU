from __future__ import annotations

"""Configuration-management tests.

Covers the DB-first runtime settings introduced for upload TTL, the global
rate-limiting toggle, the watermark master switch, and the hardened settings
service (safe coercion + '***' preservation).
"""

import datetime as dt

from sqlalchemy import select

from app.models.enums import UserRole
from app.models.media_file import MediaFile
from app.models.setting import Setting
from app.models.upload import Upload
from app.models.watermark import Watermark
from tests.helpers import real_jpeg_bytes

# --- STEP 2: upload.ttl_hours is the live source of truth -------------------


def test_upload_ttl_hours_from_db_setting(client, db):
    row = db.scalar(select(Setting).where(Setting.key == "upload.ttl_hours"))
    row.value = 5
    db.commit()

    resp = client.post(
        "/api/v1/uploads",
        files=[("files", ("a.jpg", real_jpeg_bytes(), "image/jpeg"))],
    )
    assert resp.status_code == 201, resp.text
    media_id = resp.json()["jobs"][0]["id"]

    media = db.scalar(select(MediaFile).where(MediaFile.public_id == media_id))
    upload = db.get(Upload, media.upload_id)
    delta = upload.expires_at - upload.created_at
    assert dt.timedelta(hours=4, minutes=59) <= delta <= dt.timedelta(hours=5, minutes=1)


# --- STEP 3: rate_limit.enabled is the live source of truth -----------------


def test_rate_limit_toggle_defaults_to_env_when_row_missing(client, db):
    from app.core.rate_limit import RateLimiter, rate_limiting_enabled

    assert rate_limiting_enabled() is False  # conftest sets RATE_LIMIT_ENABLED=false
    limiter = RateLimiter(None, default_limit=2)
    assert limiter.allow("key") is True


def test_rate_limit_toggle_enables_limiter(client, db):
    from app.core.rate_limit import RateLimiter, rate_limiting_enabled, reset_rate_limit_cache

    row = db.scalar(select(Setting).where(Setting.key == "rate_limit.enabled"))
    row.value = True
    db.commit()
    reset_rate_limit_cache()

    assert rate_limiting_enabled() is True
    limiter = RateLimiter(None, default_limit=2)
    assert limiter.allow("key") is True
    assert limiter.allow("key") is True
    assert limiter.allow("key") is False


def test_rate_limit_toggle_disable_via_string(client, db):
    from app.core.rate_limit import rate_limiting_enabled, reset_rate_limit_cache

    row = db.scalar(select(Setting).where(Setting.key == "rate_limit.enabled"))
    row.value = "false"
    db.commit()
    reset_rate_limit_cache()
    assert rate_limiting_enabled() is False


def test_login_throttled_when_enabled(client, db):
    from app.core.rate_limit import reset_rate_limit_cache

    row = db.scalar(select(Setting).where(Setting.key == "rate_limit.enabled"))
    row.value = True
    db.commit()
    reset_rate_limit_cache()

    limit = 10  # RATE_LIMIT_LOGIN_PER_MINUTE default
    for _ in range(limit):
        client.post(
            "/api/v1/auth/login", json={"email": "x@y.z", "password": "wrong"}
        )
    resp = client.post(
        "/api/v1/auth/login", json={"email": "x@y.z", "password": "wrong"}
    )
    assert resp.status_code == 429

# --- STEP 4: watermark.enabled is the live source of truth ------------------


def _seed_watermark_row(db) -> None:
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


def test_watermark_disabled_by_default_without_row(client, db):
    from app.services.watermark_service import get_active_watermark

    _seed_watermark_row(db)
    # No Setting row -> env fallback. WATERMARK_ENABLED is unset in tests and
    # the config default is False, matching previous production behaviour.
    assert get_active_watermark(db) is None


def test_watermark_enabled_via_db_setting(client, db):
    from app.services.watermark_service import get_active_watermark

    _seed_watermark_row(db)
    row = db.scalar(select(Setting).where(Setting.key == "watermark.enabled"))
    row.value = True
    db.commit()
    assert get_active_watermark(db) is not None

    row.value = "false"
    db.commit()
    assert get_active_watermark(db) is None


# --- STEP 5: settings service hardening --------------------------------------


def test_admin_update_keeps_masked_secret(client, auth_headers, create_user, db):
    create_user("admin@example.com", role=UserRole.ADMIN)
    headers = auth_headers("admin@example.com")

    db.add(
        Setting(
            key="smtp.password",
            value="real-secret",
            group="email",
            description="SMTP password",
            is_secret=True,
        )
    )
    db.commit()

    resp = client.put(
        "/api/v1/admin/settings",
        headers=headers,
        json=[
            {"key": "smtp.password", "value": "***"},
            {"key": "upload.ttl_hours", "value": 7},
        ],
    )
    assert resp.status_code == 200, resp.text
    stored = db.scalar(select(Setting).where(Setting.key == "smtp.password"))
    assert stored.value == "real-secret"


def test_get_setting_bool_coercion(client, db):
    from app.services.settings_service import get_setting_bool

    for raw, expected in (
        (True, True),
        (False, False),
        ("true", True),
        ("True", True),
        ("1", True),
        ("yes", True),
        ("on", True),
        ("false", False),
        ("FALSE", False),
        ("0", False),
        ("no", False),
        ("off", False),
        ("maybe", False),
    ):
        db.add(
            Setting(
                key="coercion.bool",
                value=raw,
                group="test",
                description="",
                is_secret=False,
            )
        )
        db.commit()
        assert get_setting_bool(db, "coercion.bool", False) is expected
        db.query(Setting).filter(Setting.key == "coercion.bool").delete()
        db.commit()

    assert get_setting_bool(db, "missing.key", True) is True


def test_get_setting_int_coercion(client, db):
    from app.services.settings_service import get_setting_int

    db.add(
        Setting(
            key="coercion.int",
            value="90",
            group="test",
            description="",
            is_secret=False,
        )
    )
    db.commit()
    assert get_setting_int(db, "coercion.int", 30) == 90

    db.query(Setting).filter(Setting.key == "coercion.int").update(
        {"value": "garbage"}
    )
    db.commit()
    assert get_setting_int(db, "coercion.int", 30) == 30


def test_ads_enabled_string_false_is_false(client, db):
    from app.services.ads.service import ads_enabled

    row = db.scalar(select(Setting).where(Setting.key == "ads.enabled"))
    row.value = "false"
    db.commit()
    assert ads_enabled(db) is False
