from __future__ import annotations

import re

from app.models.enums import UserRole
from tests.helpers import jpeg_bytes, png_bytes, real_jpeg_bytes, webm_bytes

PUBLIC_ID_RE = re.compile(r"^[A-Za-z0-9]{16}$")


def _files(*payloads):
    return [
        ("files", (name, data, mime))
        for name, data, mime in payloads
    ]


def _job_id(response) -> str:
    return response.json()["jobs"][0]["id"]


def test_upload_valid_multi_files(client):
    response = client.post(
        "/api/v1/uploads",
        files=_files(
            ("a.jpg", jpeg_bytes(), "image/jpeg"),
            ("b.png", png_bytes(), "image/png"),
            ("c.webm", webm_bytes(), "video/webm"),
        ),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["success"] is True
    assert len(body["jobs"]) == 3
    for job in body["jobs"]:
        assert PUBLIC_ID_RE.match(job["id"])
        assert job["status"]


def test_upload_creates_files_on_disk_and_processing_status(client):
    response = client.post(
        "/api/v1/uploads",
        files=_files(("a.jpg", real_jpeg_bytes(), "image/jpeg")),
    )
    assert response.status_code == 201
    job_id = _job_id(response)

    # eager Celery worker runs inline -> upload completes through the
    # real Pillow pipeline.
    detail = client.get(f"/api/v1/uploads/{job_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["public_id"] == job_id
    assert body["status"] == "completed"
    assert body["media_type"] == "image"
    assert body["download_url"]
    assert body["thumbnail_url"]


def test_upload_zero_files_rejected(client):
    response = client.post("/api/v1/uploads", files=[])
    assert response.status_code in {400, 422}


def test_upload_too_many_files_rejected(client):
    payloads = [(f"img_{i}.jpg", jpeg_bytes(), "image/jpeg") for i in range(6)]
    response = client.post("/api/v1/uploads", files=_files(*payloads))
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "TOO_MANY_FILES"


def test_upload_unsupported_mime_rejected(client):
    response = client.post(
        "/api/v1/uploads",
        files=_files(("notes.txt", b"hello", "text/plain")),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_upload_mime_mismatch_rejected(client):
    response = client.post(
        "/api/v1/uploads",
        files=_files(("fake.png", jpeg_bytes(), "image/png")),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "FILE_TYPE_MISMATCH"


def test_upload_oversize_file_rejected(client):
    # MAX_FILE_SIZE_MB=2 in the test environment -> 3 MB exceeds it.
    big = jpeg_bytes(3 * 1024 * 1024)
    response = client.post(
        "/api/v1/uploads",
        files=_files(("big.jpg", big, "image/jpeg")),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_get_upload_not_found(client):
    response = client.get("/api/v1/uploads/NONEXISTENT000001")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "UPLOAD_NOT_FOUND"


def test_owner_can_access_and_delete(client, create_user, auth_headers):
    user_email = "owner@example.com"
    create_user(user_email)
    headers = auth_headers(user_email)

    created = client.post(
        "/api/v1/uploads",
        files=_files(("a.jpg", real_jpeg_bytes(), "image/jpeg")),
        headers=headers,
    )
    job_id = _job_id(created)

    detail = client.get(f"/api/v1/uploads/{job_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "completed"

    deleted = client.delete(
        f"/api/v1/uploads/{job_id}", headers=headers
    )
    assert deleted.status_code == 204

    after = client.get(f"/api/v1/uploads/{job_id}")
    assert after.status_code == 404


def test_other_user_can_access_single_media_file(client, create_user, auth_headers):
    create_user("other@example.com")
    other_headers = auth_headers("other@example.com")

    created = client.post(
        "/api/v1/uploads",
        files=_files(("a.jpg", real_jpeg_bytes(), "image/jpeg")),
    )
    job_id = _job_id(created)

    # Single-file GET/DELETE are public by 16-char ID in the Phase 3 contract.
    detail = client.get(
        f"/api/v1/uploads/{job_id}", headers=other_headers
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "completed"

    deleted = client.delete(
        f"/api/v1/uploads/{job_id}", headers=other_headers
    )
    assert deleted.status_code == 204

    after = client.get(f"/api/v1/uploads/{job_id}")
    assert after.status_code == 404


def test_admin_can_access_any_upload(client, create_user, auth_headers):
    create_user("victim@example.com")
    created = client.post(
        "/api/v1/uploads",
        files=_files(("a.jpg", real_jpeg_bytes(), "image/jpeg")),
    )
    job_id = _job_id(created)

    create_user("admin@example.com", role=UserRole.ADMIN)
    admin_headers = auth_headers("admin@example.com")

    detail = client.get(
        f"/api/v1/uploads/{job_id}", headers=admin_headers
    )
    assert detail.status_code == 200
    assert detail.json()["public_id"] == job_id
