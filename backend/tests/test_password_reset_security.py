from __future__ import annotations

import datetime as dt

import pytest

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.auth_token import AuthToken
from app.services import email_service


@pytest.fixture()
def capture_emails(monkeypatch):
    sent = []

    def _send(to_email, subject, text_body, html_body=None):
        sent.append(
            {
                "to": to_email,
                "subject": subject,
                "body": text_body,
                "html": html_body,
            }
        )

    monkeypatch.setattr(email_service, "send_email", _send)
    return sent


def _extract_token(email_text: str) -> str:
    import re

    match = re.search(r"token=([A-Za-z0-9_-]+)", email_text)
    assert match, "reset link token not found in email"
    return match.group(1)


def test_forgot_password_never_returns_token(client, create_user, capture_emails):
    create_user("reset@example.com")
    response = client.post(
        "/api/v1/auth/forgot-password", json={"email": "reset@example.com"}
    )
    assert response.status_code == 200
    body = response.json()
    assert "reset_token" not in body
    assert body["message"]
    # An email was delivered with a usable link.
    assert len(capture_emails) == 1
    assert capture_emails[0]["to"] == "reset@example.com"
    assert "token=" in capture_emails[0]["body"]


def test_forgot_password_no_user_enumeration(client, create_user, capture_emails):
    create_user("exists@example.com")
    existing = client.post(
        "/api/v1/auth/forgot-password", json={"email": "exists@example.com"}
    )
    missing = client.post(
        "/api/v1/auth/forgot-password", json={"email": "nobody@example.com"}
    )
    assert existing.status_code == missing.status_code == 200
    assert existing.json() == missing.json()
    # Only the registered address received an email.
    assert len(capture_emails) == 1


def test_full_reset_flow_and_one_time_use(client, create_user, capture_emails):
    create_user("flow@example.com", password="OldPass123!")
    client.post("/api/v1/auth/forgot-password", json={"email": "flow@example.com"})
    token = _extract_token(capture_emails[0]["body"])

    # Old password still works before reset.
    login_old = client.post(
        "/api/v1/auth/login",
        json={"email": "flow@example.com", "password": "OldPass123!"},
    )
    assert login_old.status_code == 200

    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NewPass456!"},
    )
    assert reset.status_code == 200

    # Token cannot be reused.
    reuse = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "Another789!"},
    )
    assert reuse.status_code == 400
    assert reuse.json()["error"]["code"] == "INVALID_RESET_TOKEN"

    # New password works; old password no longer does.
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "flow@example.com", "password": "NewPass456!"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "flow@example.com", "password": "OldPass123!"},
        ).status_code
        in {401, 403}
    )


def test_expired_token_fails_safely(client, create_user, capture_emails):
    create_user("expired@example.com", password="OldPass123!")
    client.post("/api/v1/auth/forgot-password", json={"email": "expired@example.com"})
    token = _extract_token(capture_emails[0]["body"])

    with SessionLocal() as db:
        row = db.query(AuthToken).first()
        row.expires_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)
        db.commit()

    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NewPass456!"},
    )
    assert reset.status_code == 400
    assert reset.json()["error"]["code"] == "INVALID_RESET_TOKEN"


def test_invalid_token_fails_safely(client, create_user):
    create_user("invalid@example.com")
    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "not-a-real-token", "new_password": "NewPass456!"},
    )
    assert reset.status_code == 400
    assert reset.json()["error"]["code"] == "INVALID_RESET_TOKEN"


def test_weak_password_rejected(client, create_user, capture_emails):
    create_user("weak@example.com")
    client.post("/api/v1/auth/forgot-password", json={"email": "weak@example.com"})
    token = _extract_token(capture_emails[0]["body"])
    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "short"},
    )
    assert reset.status_code in {400, 422}
