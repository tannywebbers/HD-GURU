from __future__ import annotations

import datetime as dt
import uuid

import pytest

from app.core.security import hash_password
from app.models.api_key import ApiKey
from app.models.enums import JobStatus, MediaStatus, UserRole
from app.models.job import Job
from app.models.login_history import LoginHistory
from app.models.media_file import MediaFile
from app.models.upload import Upload
from app.models.watermark import Watermark


# --- role gating ------------------------------------------------------------


def test_admin_requires_authentication(client):
    assert client.get("/api/v1/admin/dashboard").status_code == 401
    assert client.get("/api/v1/admin/me").status_code == 401


def test_admin_forbidden_for_regular_user(client, auth_headers, create_user):
    create_user("user@example.com", role=UserRole.USER)
    headers = auth_headers("user@example.com")
    assert client.get("/api/v1/admin/dashboard", headers=headers).status_code == 403
    assert client.get("/api/v1/admin/me", headers=headers).status_code == 403


def test_viewer_role_can_read_but_not_write(client, auth_headers, create_user):
    create_user("viewer@example.com", role=UserRole.VIEWER)
    headers = auth_headers("viewer@example.com")
    assert client.get("/api/v1/admin/dashboard", headers=headers).status_code == 200
    assert client.get("/api/v1/admin/users", headers=headers).status_code == 200
    assert client.post("/api/v1/admin/users", headers=headers, json={}).status_code == 403
    assert (
        client.delete("/api/v1/admin/watermark/00000000-0000-0000-0000-000000000000", headers=headers).status_code
        == 403
    )


def test_admin_me_returns_permissions(client, auth_headers, create_user):
    create_user("admin@example.com", role=UserRole.ADMIN)
    headers = auth_headers("admin@example.com")
    body = client.get("/api/v1/admin/me", headers=headers).json()
    assert body["role"] == "admin"
    assert "dashboard.view" in body["permissions"]
    assert "users.manage" in body["permissions"]
    assert "whatsapp.credentials" in body["permissions"]


def test_super_admin_has_all_permissions(client, auth_headers, create_user):
    create_user("root@example.com", role=UserRole.SUPER_ADMIN)
    headers = auth_headers("root@example.com")
    body = client.get("/api/v1/admin/me", headers=headers).json()
    assert "security.manage" in body["permissions"]
    assert "settings.manage" in body["permissions"]


def test_operator_cannot_manage_users(client, auth_headers, create_user):
    create_user("op@example.com", role=UserRole.OPERATOR)
    headers = auth_headers("op@example.com")
    assert client.get("/api/v1/admin/users", headers=headers).status_code == 200
    resp = client.put(
        "/api/v1/admin/users/00000000-0000-0000-0000-000000000000",
        headers=headers,
        json={"role": "viewer"},
    )
    assert resp.status_code == 403


# --- dashboard --------------------------------------------------------------


def test_dashboard_returns_counters_and_health(client, auth_headers, create_user, db):
    create_user("admin@example.com", role=UserRole.ADMIN)
    upload = Upload(
        public_id="A" * 16,
        original_filename="a.jpg",
        mime_type="image/jpeg",
        extension="jpg",
        file_size=10,
        storage_location="/tmp/x",
        status=MediaStatus.COMPLETED,
        file_count=1,
        download_count=3,
        whatsapp_delivery_count=2,
        expires_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1),
    )
    db.add(upload)
    db.commit()
    headers = auth_headers("admin@example.com")
    body = client.get("/api/v1/admin/dashboard", headers=headers).json()
    assert body["counters"]["uploads_total"] == 1
    assert body["counters"]["downloads_total"] == 3
    assert body["counters"]["whatsapp_deliveries_total"] == 2
    assert body["health"]["components"]["application"]["status"] == "ok"
    assert body["system"]["version"]


# --- media ------------------------------------------------------------------


def _make_upload(db, public_id="B" * 16) -> Upload:
    upload = Upload(
        public_id=public_id,
        original_filename="photo.jpg",
        mime_type="image/jpeg",
        extension="jpg",
        file_size=10,
        storage_location="/tmp/x",
        status=MediaStatus.COMPLETED,
        file_count=1,
        download_count=0,
        whatsapp_delivery_count=0,
        expires_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1),
    )
    db.add(upload)
    db.flush()
    return upload


def _make_media(db, upload, public_id="C" * 16) -> MediaFile:
    media = MediaFile(
        public_id=public_id,
        upload_id=upload.id,
        seq=1,
        original_filename="photo.jpg",
        stored_filename="1_photo.jpg",
        mime_type="image/jpeg",
        extension="jpg",
        file_size=10,
        storage_location="/tmp/x",
        status=MediaStatus.COMPLETED,
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    return media


def test_media_list_and_delete(client, auth_headers, create_user, db):
    create_user("admin@example.com", role=UserRole.ADMIN)
    upload = _make_upload(db)
    media = _make_media(db, upload)
    headers = auth_headers("admin@example.com")

    body = client.get("/api/v1/admin/media", headers=headers).json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["public_id"] == media.public_id
    assert item["upload_public_id"] == upload.public_id
    assert item["status"] == "completed"

    resp = client.delete(f"/api/v1/admin/media/{media.public_id}", headers=headers)
    assert resp.status_code == 204
    assert client.get("/api/v1/admin/media", headers=headers).json()["total"] == 0


def test_media_search_and_pagination(client, auth_headers, create_user, db):
    create_user("admin@example.com", role=UserRole.ADMIN)
    upload = _make_upload(db)
    for seq in range(1, 4):
        db.add(
            MediaFile(
                public_id=f"D{seq:015d}",
                upload_id=upload.id,
                seq=seq,
                original_filename=f"file{seq}.jpg",
                stored_filename=f"{seq}_file.jpg",
                mime_type="image/jpeg",
                extension="jpg",
                file_size=10,
                storage_location="/tmp/x",
                status=MediaStatus.COMPLETED,
            )
        )
    db.commit()
    headers = auth_headers("admin@example.com")
    body = client.get(
        "/api/v1/admin/media?search=file2", headers=headers
    ).json()
    assert body["total"] == 1
    body = client.get(
        "/api/v1/admin/media?per_page=2&page=1", headers=headers
    ).json()
    assert len(body["items"]) == 2
    assert body["pages"] == 2


# --- jobs -------------------------------------------------------------------


def test_jobs_list_and_retry(client, auth_headers, create_user, db):
    create_user("admin@example.com", role=UserRole.ADMIN)
    upload = _make_upload(db)
    job = Job(
        job_type="uploads.process",
        status=JobStatus.FAILED,
        upload_id=upload.id,
        args={"public_id": upload.public_id},
        retries=3,
        max_retries=3,
        traceback="boom",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    headers = auth_headers("admin@example.com")

    body = client.get("/api/v1/admin/jobs", headers=headers).json()
    assert body["total"] == 1
    # traceback must never be exposed
    assert "traceback" not in body["items"][0]

    resp = client.post(f"/api/v1/admin/jobs/{job.id}/retry", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "queued"
    assert data["celery_task_id"]


def test_retry_rejects_running_job(client, auth_headers, create_user, db):
    create_user("admin@example.com", role=UserRole.ADMIN)
    upload = _make_upload(db)
    job = Job(
        job_type="uploads.process",
        status=JobStatus.RUNNING,
        upload_id=upload.id,
        args={"public_id": upload.public_id},
    )
    db.add(job)
    db.commit()
    headers = auth_headers("admin@example.com")
    resp = client.post(f"/api/v1/admin/jobs/{job.id}/retry", headers=headers)
    assert resp.status_code == 409


# --- users ------------------------------------------------------------------


def test_users_crud(client, auth_headers, create_user, db):
    create_user("admin@example.com", role=UserRole.ADMIN)
    headers = auth_headers("admin@example.com")

    resp = client.post(
        "/api/v1/admin/users",
        headers=headers,
        json={
            "email": "new@example.com",
            "password": "Str0ngPass!",
            "full_name": "New User",
            "role": "viewer",
        },
    )
    assert resp.status_code == 201, resp.text
    user = resp.json()
    assert user["role"] == "viewer"
    assert user["must_change_password"] is True

    user_id = user["id"]
    resp = client.put(
        f"/api/v1/admin/users/{user_id}",
        headers=headers,
        json={"role": "operator", "is_active": False},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "operator"
    assert resp.json()["is_active"] is False

    resp = client.delete(f"/api/v1/admin/users/{user_id}", headers=headers)
    assert resp.status_code == 204


def test_user_self_protection(client, auth_headers, create_user, db):
    admin = create_user("admin@example.com", role=UserRole.ADMIN)
    headers = auth_headers("admin@example.com")
    resp = client.put(
        f"/api/v1/admin/users/{admin.id}",
        headers=headers,
        json={"is_active": False},
    )
    assert resp.status_code == 400
    resp = client.delete(f"/api/v1/admin/users/{admin.id}", headers=headers)
    assert resp.status_code == 400


def test_users_invalid_role(client, auth_headers, create_user):
    create_user("admin@example.com", role=UserRole.ADMIN)
    headers = auth_headers("admin@example.com")
    resp = client.post(
        "/api/v1/admin/users",
        headers=headers,
        json={"email": "x@example.com", "password": "Str0ngPass!", "role": "nope"},
    )
    assert resp.status_code == 400


# --- whatsapp ---------------------------------------------------------------


def test_whatsapp_overview_masks_secrets(client, auth_headers, create_user):
    create_user("admin@example.com", role=UserRole.ADMIN)
    headers = auth_headers("admin@example.com")
    body = client.get("/api/v1/admin/whatsapp/overview", headers=headers).json()
    assert body["messages_total"] == 0
    assert body["webhook"]["credentials_configured"] is False
    assert "access_token" not in body["config"]
    assert "app_secret" not in body["config"]
    assert body["config"]["access_token_masked"] is None


def test_whatsapp_config_update_masked(client, auth_headers, create_user):
    create_user("admin@example.com", role=UserRole.ADMIN)
    headers = auth_headers("admin@example.com")
    resp = client.put(
        "/api/v1/admin/whatsapp/config",
        headers=headers,
        json={"phone_number": "+15551234567", "access_token": "SUPERSECRETTOKEN123"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["phone_number"] == "+15551234567"
    assert "SUPERSECRETTOKEN123" not in resp.text
    assert body["access_token_masked"] is not None


def test_whatsapp_config_update_requires_credentials_perm(client, auth_headers, create_user):
    create_user("op@example.com", role=UserRole.OPERATOR)
    headers = auth_headers("op@example.com")
    resp = client.put("/api/v1/admin/whatsapp/config", headers=headers, json={})
    assert resp.status_code == 403


def test_whatsapp_connection_test_without_credentials(client, auth_headers, create_user):
    create_user("admin@example.com", role=UserRole.ADMIN)
    headers = auth_headers("admin@example.com")
    resp = client.post("/api/v1/admin/whatsapp/test", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is False


# --- watermark --------------------------------------------------------------


def test_watermark_crud(client, auth_headers, create_user, db):
    create_user("admin@example.com", role=UserRole.ADMIN)
    headers = auth_headers("admin@example.com")

    resp = client.post(
        "/api/v1/admin/watermark",
        headers=headers,
        json={
            "name": "brand",
            "type": "text",
            "text": "HD Guru",
            "position": "middle-center",
            "opacity": 0.4,
            "size_percent": 9.0,
            "margin": 24,
            "enabled": True,
        },
    )
    assert resp.status_code == 201, resp.text
    watermark = resp.json()
    assert watermark["margin"] == 24

    resp = client.put(
        f"/api/v1/admin/watermark/{watermark['id']}",
        headers=headers,
        json={"opacity": 0.7},
    )
    assert resp.status_code == 200
    assert resp.json()["opacity"] == 0.7

    rows = client.get("/api/v1/admin/watermark", headers=headers).json()
    assert any(row["name"] == "brand" for row in rows)

    resp = client.delete(f"/api/v1/admin/watermark/{watermark['id']}", headers=headers)
    assert resp.status_code == 204


def test_watermark_validation(client, auth_headers, create_user):
    create_user("admin@example.com", role=UserRole.ADMIN)
    headers = auth_headers("admin@example.com")
    resp = client.post(
        "/api/v1/admin/watermark",
        headers=headers,
        json={"name": "x", "type": "text", "text": "  ", "position": "corner"},
    )
    assert resp.status_code == 400


# --- settings ---------------------------------------------------------------


def test_settings_masked_for_admin(client, auth_headers, create_user, db):
    create_user("admin@example.com", role=UserRole.ADMIN)
    from app.models.setting import Setting

    db.add(
        Setting(
            key="secret.key",
            value="hunter2",
            group="secrets",
            description="Secret",
            is_secret=True,
        )
    )
    db.commit()
    headers = auth_headers("admin@example.com")
    body = client.get("/api/v1/admin/settings", headers=headers).json()
    values = {s["key"]: s["value"] for s in body["settings"]}
    assert values["secret.key"] == "***"
    assert "hunter2" not in str(body)


def test_settings_update_and_keep_secret(client, auth_headers, create_user, db):
    create_user("admin@example.com", role=UserRole.ADMIN)
    from app.models.setting import Setting

    db.add(
        Setting(
            key="branding.tagline",
            value="Old",
            group="general",
            description="App tagline",
            is_secret=False,
        )
    )
    db.commit()
    headers = auth_headers("admin@example.com")
    resp = client.put(
        "/api/v1/admin/settings",
        headers=headers,
        json=[{"key": "branding.tagline", "value": "HD Guru Pro"}],
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert any(
        s["key"] == "branding.tagline" and s["value"] == "HD Guru Pro"
        for s in body["settings"]
    )


# --- logs & audit -----------------------------------------------------------


def test_logs_and_audit_pagination(client, auth_headers, create_user, db):
    create_user("admin@example.com", role=UserRole.ADMIN)
    from app.models.audit_log import AuditLog
    from app.models.system_log import SystemLog

    db.add(SystemLog(level="ERROR", logger_name="worker", message="boom", context={}))
    db.add(AuditLog(actor_type="system", action="test.action", details={}))
    db.commit()
    headers = auth_headers("admin@example.com")

    logs = client.get("/api/v1/admin/logs", headers=headers).json()
    assert logs["total"] == 1
    assert logs["items"][0]["message"] == "boom"

    audit = client.get(
        "/api/v1/admin/audit-logs?action=test.action", headers=headers
    ).json()
    assert audit["total"] == 1
    assert audit["items"][0]["action"] == "test.action"


def test_logs_level_filter(client, auth_headers, create_user, db):
    create_user("admin@example.com", role=UserRole.ADMIN)
    from app.models.system_log import SystemLog

    db.add(SystemLog(level="INFO", logger_name="app", message="ok", context={}))
    db.commit()
    headers = auth_headers("admin@example.com")
    body = client.get("/api/v1/admin/logs?level=ERROR", headers=headers).json()
    assert body["total"] == 0


# --- security ---------------------------------------------------------------


def test_security_endpoints(client, auth_headers, create_user, db):
    admin = create_user("admin@example.com", role=UserRole.ADMIN)
    headers = auth_headers("admin@example.com")

    db.add(
        LoginHistory(
            email="admin@example.com",
            success=True,
            user_id=admin.id,
            ip_address="1.2.3.4",
        )
    )
    db.add(
        ApiKey(
            user_id=admin.id,
            name="test key",
            key_hash="x" * 64,
            key_prefix="hdgur",
            scopes=["uploads"],
            is_active=True,
        )
    )
    db.commit()
    db.flush()
    key = db.query(ApiKey).filter_by(name="test key").one()

    overview = client.get("/api/v1/admin/security/overview", headers=headers).json()
    assert overview["users_total"] >= 1
    assert overview["active_api_keys"] == 1

    history = client.get("/api/v1/admin/security/login-history", headers=headers).json()
    assert history["total"] >= 1
    assert any(item["email"] == "admin@example.com" for item in history["items"])

    keys = client.get("/api/v1/admin/security/api-keys", headers=headers).json()
    assert keys[0]["name"] == "test key"
    assert "key_hash" not in keys[0]

    resp = client.post(
        f"/api/v1/admin/security/api-keys/{key.id}/revoke", headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    resp = client.post(
        f"/api/v1/admin/security/users/{admin.id}/logout-all", headers=headers
    )
    assert resp.status_code == 200


# --- health -----------------------------------------------------------------


def test_admin_health(client, auth_headers, create_user):
    create_user("admin@example.com", role=UserRole.ADMIN)
    headers = auth_headers("admin@example.com")
    body = client.get("/api/v1/admin/health", headers=headers).json()
    assert body["status"] in ("ok", "degraded")
    assert body["components"]["database"]["status"] == "ok"
    assert "workers" in body
