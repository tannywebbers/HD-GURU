from __future__ import annotations

from app.models.enums import UserRole


def test_settings_require_auth(client):
    response = client.get("/api/v1/settings")
    assert response.status_code == 401


def test_settings_visible_to_user(client, create_user, auth_headers):
    create_user("viewer@example.com")
    headers = auth_headers("viewer@example.com")
    response = client.get("/api/v1/settings", headers=headers)
    assert response.status_code == 200
    keys = {item["key"] for item in response.json()["settings"]}
    assert "upload.max_upload_count" in keys


def test_user_cannot_update_settings(client, create_user, auth_headers):
    create_user("editor@example.com")
    headers = auth_headers("editor@example.com")
    response = client.put(
        "/api/v1/settings",
        json={"settings": [{"key": "upload.ttl_hours", "value": 48}]},
        headers=headers,
    )
    assert response.status_code == 403


def test_admin_can_update_settings(client, create_user, auth_headers):
    create_user("boss@example.com", role=UserRole.ADMIN)
    headers = auth_headers("boss@example.com")
    response = client.put(
        "/api/v1/settings",
        json={"settings": [{"key": "upload.ttl_hours", "value": 48}]},
        headers=headers,
    )
    assert response.status_code == 200
    updated = {
        item["key"]: item["value"]
        for item in response.json()["settings"]
    }
    assert updated["upload.ttl_hours"] == 48


def test_admin_update_unknown_setting(client, create_user, auth_headers):
    create_user("boss2@example.com", role=UserRole.ADMIN)
    headers = auth_headers("boss2@example.com")
    response = client.put(
        "/api/v1/settings",
        json={"settings": [{"key": "nope.missing", "value": 1}]},
        headers=headers,
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SETTING_NOT_FOUND"
