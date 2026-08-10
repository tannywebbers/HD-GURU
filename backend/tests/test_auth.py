from __future__ import annotations


def test_login_success(client, create_user):
    create_user("alice@example.com", "Str0ngPass!")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "Str0ngPass!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


def test_login_wrong_password(client, create_user):
    create_user("bob@example.com", "Str0ngPass!")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "bob@example.com", "password": "WrongPass!"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_unknown_user(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@example.com", "password": "whatever"},
    )
    assert response.status_code == 401


def test_login_email_case_insensitive(client, create_user):
    create_user("case@example.com", "Str0ngPass!")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "CASE@example.com", "password": "Str0ngPass!"},
    )
    assert response.status_code == 200


def test_me_requires_auth(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_me_with_token(client, create_user, auth_headers):
    email = "me@example.com"
    create_user(email)
    headers = auth_headers(email)
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == email


def test_refresh_flow(client, create_user):
    create_user("refresh@example.com")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "refresh@example.com", "password": "Str0ngPass!"},
    ).json()

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login["refresh_token"]},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_refresh_token_is_single_use(client, create_user):
    create_user("single@example.com")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "single@example.com", "password": "Str0ngPass!"},
    ).json()
    refresh_token = login["refresh_token"]

    first = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert first.status_code == 200

    second = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert second.status_code == 401


def test_logout_revokes_refresh(client, create_user):
    create_user("logout@example.com")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "logout@example.com", "password": "Str0ngPass!"},
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": login["refresh_token"]},
        headers=headers,
    )
    assert response.status_code == 204

    refresh_after = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login["refresh_token"]},
    )
    assert refresh_after.status_code == 401
