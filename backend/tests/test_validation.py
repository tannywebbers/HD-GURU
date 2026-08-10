from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.exceptions import AppError
from app.utils.files import validate_file

VALID = dict(
    DATABASE_URL="postgresql+psycopg://u:p@localhost/db",
    JWT_SECRET_KEY="x" * 32,
    MAX_UPLOAD_COUNT=5,
    MAX_FILE_SIZE_MB=100,
    MAX_UPLOAD_SIZE_MB=500,
    ALLOWED_MIME_TYPES="image/jpeg,video/mp4",
    CORS_ORIGINS="*",
    ALLOWED_HOSTS="*",
)


def _settings(**overrides) -> Settings:
    data = {**VALID, **overrides}
    return Settings(**data)


def test_valid_settings():
    settings = _settings()
    assert settings.max_file_size_bytes == 100 * 1024 * 1024
    assert settings.allowed_mime_types == ["image/jpeg", "video/mp4"]


def test_jwt_secret_must_be_long():
    with pytest.raises(ValidationError):
        _settings(JWT_SECRET_KEY="short")


def test_upload_count_must_be_positive():
    with pytest.raises(ValidationError):
        _settings(MAX_UPLOAD_COUNT=0)
    with pytest.raises(ValidationError):
        _settings(MAX_UPLOAD_COUNT=11)


def test_upload_size_must_be_positive():
    with pytest.raises(ValidationError):
        _settings(MAX_FILE_SIZE_MB=0)
    with pytest.raises(ValidationError):
        _settings(MAX_UPLOAD_SIZE_MB=-1)


def test_mime_types_must_not_be_empty():
    with pytest.raises(ValidationError):
        _settings(ALLOWED_MIME_TYPES="   ")


def test_database_url_required():
    with pytest.raises(ValidationError):
        _settings(DATABASE_URL="")


# --- file validation ----------------------------------------------------------
def test_valid_jpeg_file():
    mime, ext = validate_file(
        "photo.jpg", "image/jpeg", b"\xff\xd8\xff\xe0" + b"\x00" * 100,
        ["image/jpeg"], max_file_size=1024 * 1024, max_upload_size=10 * 1024 * 1024,
        current_total=0,
    )
    assert mime == "image/jpeg"
    assert ext == "jpg"


def test_mime_mismatch_rejected():
    with pytest.raises(AppError) as exc_info:
        validate_file(
            "fake.png", "image/png", b"\xff\xd8\xff\xe0" + b"\x00" * 100,
            ["image/jpeg", "image/png"], max_file_size=1024 * 1024,
            max_upload_size=10 * 1024 * 1024, current_total=0,
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "FILE_TYPE_MISMATCH"


def test_unsupported_format_rejected():
    with pytest.raises(AppError) as exc_info:
        validate_file(
            "notes.txt", "text/plain", b"hello world",
            ["image/jpeg"], max_file_size=1024 * 1024,
            max_upload_size=10 * 1024 * 1024, current_total=0,
        )
    assert exc_info.value.error_code == "UNSUPPORTED_FILE_TYPE"


def test_empty_file_rejected():
    with pytest.raises(AppError) as exc_info:
        validate_file(
            "empty.jpg", "image/jpeg", b"",
            ["image/jpeg"], max_file_size=1024 * 1024,
            max_upload_size=10 * 1024 * 1024, current_total=0,
        )
    assert exc_info.value.error_code == "EMPTY_FILE"


def test_file_too_large_rejected():
    with pytest.raises(AppError) as exc_info:
        validate_file(
            "big.jpg", "image/jpeg", b"\xff\xd8\xff" + b"\x00" * 2048,
            ["image/jpeg"], max_file_size=1024,
            max_upload_size=10 * 1024, current_total=0,
        )
    assert exc_info.value.error_code == "FILE_TOO_LARGE"


# --- API request validation ----------------------------------------------------
def test_invalid_login_body_returns_422(client):
    response = client.post("/api/v1/auth/login", json={"email": "not-an-email"})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"]
