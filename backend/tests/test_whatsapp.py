from __future__ import annotations

import hashlib
import hmac
import json

from sqlalchemy import select

from app.models.enums import UserRole, WhatsAppEventStatus
from app.models.whatsapp import WhatsappWebhookEvent
from app.services.whatsapp import config as whatsapp_config

VERIFY_TOKEN = "verify-me-token"
APP_SECRET = "super-secret-app-secret"


def _signature(body: bytes, secret: str = APP_SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _configure(db, **overrides):
    defaults = dict(
        enabled=True,
        phone_number_id="123456789012345",
        phone_number="+15551234567",
        business_account_id="102290129340398",
        access_token="EAATestToken1234567890",
        verify_token=VERIFY_TOKEN,
        app_secret=APP_SECRET,
    )
    defaults.update(overrides)
    return whatsapp_config.upsert_config(db, **defaults)


def _status_payload() -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "102290129340398",
                "changes": [
                    {
                        "value": {
                            "statuses": [
                                {
                                    "id": "wamid.ABXYZ",
                                    "status": "sent",
                                    "timestamp": "1723000000",
                                    "recipient_id": "15559876543",
                                }
                            ]
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


def _message_payload() -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "102290129340398",
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "15559876543",
                                    "id": "wamid.IN1",
                                    "timestamp": "1723000000",
                                    "type": "text",
                                    "text": {"body": "Send HD for HD7K2P9X4M8QW3ZT"},
                                }
                            ]
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


def _post_webhook(client, payload, *, signature: str):
    body = json.dumps(payload).encode("utf-8")
    return client.post(
        "/api/v1/whatsapp/webhook",
        content=body,
        headers={"X-Hub-Signature-256": signature},
    )


# --- GET verification handshake ---------------------------------------------


def test_webhook_verify_returns_challenge(client, db):
    _configure(db)
    response = client.get(
        "/api/v1/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": VERIFY_TOKEN,
            "hub.challenge": "CHALLENGE_123",
        },
    )
    assert response.status_code == 200
    assert response.text == "CHALLENGE_123"


def test_webhook_verify_rejects_wrong_token(client, db):
    _configure(db)
    response = client.get(
        "/api/v1/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "not-the-token",
            "hub.challenge": "CHALLENGE_123",
        },
    )
    assert response.status_code == 403


def test_webhook_verify_rejects_bad_mode(client, db):
    _configure(db)
    response = client.get(
        "/api/v1/whatsapp/webhook",
        params={
            "hub.mode": "unsubscribe",
            "hub.verify_token": VERIFY_TOKEN,
            "hub.challenge": "CHALLENGE_123",
        },
    )
    assert response.status_code == 403


def test_webhook_verify_rejects_when_unconfigured(client):
    response = client.get(
        "/api/v1/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": VERIFY_TOKEN,
            "hub.challenge": "CHALLENGE_123",
        },
    )
    assert response.status_code == 403


# --- POST webhook signature validation ---------------------------------------


def test_webhook_post_without_signature_rejected(client, db):
    _configure(db)
    response = client.post("/api/v1/whatsapp/webhook", json=_status_payload())
    assert response.status_code == 403


def test_webhook_post_with_bad_signature_rejected(client, db):
    _configure(db)
    response = _post_webhook(
        client, _status_payload(), signature="sha256=" + "0" * 64
    )
    assert response.status_code == 403


def test_webhook_post_valid_signature_persists_and_ignores_when_disabled(client, db):
    _configure(db, enabled=False)
    response = _post_webhook(client, _status_payload(), signature=_signature(json.dumps(_status_payload()).encode()))
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "events": 1}
    event = db.scalars(select(WhatsappWebhookEvent)).one()
    assert event.status == WhatsAppEventStatus.IGNORED


def test_webhook_post_enqueues_events_when_enabled(client, db, monkeypatch):
    _configure(db)
    enqueued: list[str] = []

    class FakeTask:
        @staticmethod
        def delay(event_id: str):
            enqueued.append(event_id)

    import app.api.v1.endpoints.whatsapp as endpoint_mod

    monkeypatch.setattr(endpoint_mod, "process_whatsapp_event", FakeTask)

    payload = _message_payload()
    response = _post_webhook(client, payload, signature=_signature(json.dumps(payload).encode()))
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "events": 1}
    assert len(enqueued) == 1
    event = db.scalars(select(WhatsappWebhookEvent)).one()
    assert event.event_type == "message"
    assert event.status == WhatsAppEventStatus.RECEIVED


def test_webhook_post_rejects_invalid_json_when_signature_ok(client, db):
    _configure(db)
    body = b"not json at all"
    response = client.post(
        "/api/v1/whatsapp/webhook",
        content=body,
        headers={"X-Hub-Signature-256": _signature(body)},
    )
    assert response.status_code == 400


# --- admin configuration -----------------------------------------------------


def test_config_requires_auth(client):
    response = client.get("/api/v1/whatsapp/config")
    assert response.status_code == 401


def test_config_forbidden_for_user(client, create_user, auth_headers):
    create_user("viewer@example.com")
    headers = auth_headers("viewer@example.com")
    assert client.get("/api/v1/whatsapp/config", headers=headers).status_code == 403
    assert (
        client.put(
            "/api/v1/whatsapp/config", json={"enabled": True}, headers=headers
        ).status_code
        == 403
    )


def test_admin_get_config_masks_secrets(client, create_user, auth_headers, db):
    _configure(db, access_token="EAATokenVeryLongSecret1234567890")
    create_user("boss@example.com", role=UserRole.ADMIN)
    headers = auth_headers("boss@example.com")
    response = client.get("/api/v1/whatsapp/config", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["token_configured"] is True
    assert body["access_token_masked"] is not None
    assert "EAAToken" not in json.dumps(body)


def test_admin_update_config_never_echoes_secrets(client, create_user, auth_headers, db):
    create_user("boss@example.com", role=UserRole.ADMIN)
    headers = auth_headers("boss@example.com")
    response = client.put(
        "/api/v1/whatsapp/config",
        json={
            "enabled": True,
            "phone_number": "+15551234567",
            "access_token": "EAATokenVeryLongSecret1234567890",
            "verify_token": VERIFY_TOKEN,
            "app_secret": APP_SECRET,
        },
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["phone_number"] == "+15551234567"
    assert "EAATokenVeryLongSecret" not in json.dumps(body)
    assert "super-secret-app-secret" not in json.dumps(body)


def test_test_connection_reports_unconfigured_safely(client, create_user, auth_headers, db):
    create_user("boss@example.com", role=UserRole.ADMIN)
    headers = auth_headers("boss@example.com")
    response = client.post("/api/v1/whatsapp/config/test", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False


def test_webhook_status_admin_only(client, create_user, auth_headers):
    create_user("viewer@example.com")
    headers = auth_headers("viewer@example.com")
    assert client.get("/api/v1/whatsapp/webhook/status", headers=headers).status_code == 403


# --- public config + wa.me link ---------------------------------------------


def test_public_config_is_open_and_safe(client, db):
    _configure(db)
    response = client.get("/api/v1/public/whatsapp")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["phone_number"] == "+15551234567"
    assert body["message_template"] == "Send HD for {ID}"
    assert "EAATestToken" not in json.dumps(body)
    assert "verify-me-token" not in json.dumps(body)


def test_build_whatsapp_link_only_when_enabled(db):
    public_id = "HD7K2P9X4M8QW3ZT"
    _configure(db, enabled=True)
    link = whatsapp_config.build_whatsapp_link(public_id, db)
    assert link is not None
    assert link.startswith("https://wa.me/15551234567?text=")
    assert "Send%20HD%20for%20" in link
    assert public_id in link

    _configure(db, enabled=False)
    assert whatsapp_config.build_whatsapp_link(public_id, db) is None
