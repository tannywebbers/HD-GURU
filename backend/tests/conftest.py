from __future__ import annotations

import os
import shutil
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///./test_hdguru.db"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-longer-than-32-characters"
os.environ["REDIS_URL"] = "redis://localhost:6379/9"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["CELERY_TASK_EAGER_PROPAGATES"] = "false"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["MAX_FILE_SIZE_MB"] = "2"
os.environ["MAX_UPLOAD_SIZE_MB"] = "8"
os.environ["MAX_UPLOAD_COUNT"] = "5"
os.environ["STORAGE_DIR"] = "./test_storage"
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "false"

from typing import Generator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.database import SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402,F401
from app.models.enums import UserRole  # noqa: E402
from app.models.user import User  # noqa: E402


@pytest.fixture(autouse=True)
def reset_db_and_storage():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    storage = Path(os.environ["STORAGE_DIR"])
    if storage.exists():
        shutil.rmtree(storage)
    yield


@pytest.fixture()
def db(reset_db_and_storage) -> Generator[Session, None, None]:
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def client(reset_db_and_storage):
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def create_user(db):
    def _create(
        email: str,
        password: str = "Str0ngPass!",
        role: UserRole = UserRole.USER,
        active: bool = True,
    ) -> User:
        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name="Test User",
            role=role,
            is_active=active,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _create


@pytest.fixture()
def auth_headers(client, create_user):
    def _headers(email: str, password: str = "Str0ngPass!") -> dict:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert response.status_code == 200, response.text
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _headers


# --- sample media payloads ---------------------------------------------------
from tests.helpers import jpeg_bytes, png_bytes, webm_bytes  # noqa: F401
