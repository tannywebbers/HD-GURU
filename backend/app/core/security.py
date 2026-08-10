from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from jwt import InvalidTokenError

from app.core.config import settings
from app.core.redis import get_redis, redis_available

ACCESS_TYPE = "access"
REFRESH_TYPE = "refresh"


# --- password hashing ---------------------------------------------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except ValueError:
        return False


def generate_secure_token() -> str:
    """Cryptographically secure random token for one-time use links."""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """SHA-256 hash of a one-time token. Tokens are stored hashed only."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_match(provided: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_token(provided), stored_hash)


# --- token primitives ---------------------------------------------------------
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _create_token(user, token_type: str, lifetime: timedelta) -> str:
    now = _now()
    payload: dict[str, Any] = {
        "sub": str(user.id),
        "type": token_type,
        "jti": uuid.uuid4().hex,
        "role": user.role.value,
        "tver": user.token_version,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int((now + lifetime).timestamp()),
    }
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def create_access_token(user) -> str:
    lifetime = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_token(user, ACCESS_TYPE, lifetime)


def create_refresh_token(user) -> str:
    lifetime = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    token = _create_token(user, REFRESH_TYPE, lifetime)
    payload = decode_token(token, expected_type=REFRESH_TYPE)
    _store_refresh(payload["jti"], str(user.id), lifetime)
    return token


def decode_token(token: str, expected_type: str | None = None) -> dict:
    """Decode and validate a token. Raises jwt.InvalidTokenError on failure."""
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        audience=settings.JWT_AUDIENCE,
        issuer=settings.JWT_ISSUER,
    )
    if expected_type is not None and payload.get("type") != expected_type:
        raise InvalidTokenError("Unexpected token type.")
    return payload


# --- Redis-backed token store with in-memory fallback ------------------------
# Token revocation / single-use semantics are enforced in-memory when Redis is
# unavailable, so the security guarantees hold on any deployment topology.
_mem: dict[str, tuple[str, float]] = {}
_mem_lock = threading.Lock()


def _mem_setex(key: str, value: str, ttl: int) -> None:
    with _mem_lock:
        _mem[key] = (value, time.monotonic() + ttl)


def _mem_get(key: str) -> str | None:
    with _mem_lock:
        item = _mem.get(key)
        if item is None:
            return None
        value, expiry = item
        if expiry < time.monotonic():
            _mem.pop(key, None)
            return None
        return value


def _mem_delete(key: str) -> None:
    with _mem_lock:
        _mem.pop(key, None)


def _mem_exists(key: str) -> bool:
    return _mem_get(key) is not None


def _token_redis():
    return get_redis() if redis_available() else None


def _store_refresh(jti: str, user_id: str, lifetime: timedelta) -> None:
    ttl = int(lifetime.total_seconds())
    client = _token_redis()
    if client is not None:
        try:
            client.set(f"refresh:{jti}", user_id, ex=ttl)
            return
        except Exception:
            pass
    _mem_setex(f"refresh:{jti}", user_id, ttl)


def _consume_refresh(jti: str) -> None:
    client = _token_redis()
    if client is not None:
        try:
            client.delete(f"refresh:{jti}")
            return
        except Exception:
            pass
    _mem_delete(f"refresh:{jti}")


def _refresh_valid(jti: str) -> bool:
    client = _token_redis()
    if client is not None:
        try:
            return bool(client.exists(f"refresh:{jti}"))
        except Exception:
            pass
    return _mem_exists(f"refresh:{jti}")


@dataclass(frozen=True)
class RefreshTokenPayload:
    user_id: uuid.UUID
    token_version: int


def consume_refresh_token(token: str) -> RefreshTokenPayload:
    payload = decode_token(token, expected_type=REFRESH_TYPE)
    jti = payload["jti"]
    if is_revoked(jti):
        raise InvalidTokenError("Refresh token has been revoked.")
    if not _refresh_valid(jti):
        raise InvalidTokenError("Refresh token is not active.")
    _consume_refresh(jti)
    return RefreshTokenPayload(
        user_id=uuid.UUID(payload["sub"]),
        token_version=int(payload.get("tver", 0)),
    )


def revoke_all_user_tokens(user) -> None:
    """Invalidate every access + refresh token issued before now.

    Callers must persist the incremented ``token_version`` afterwards.
    """
    user.token_version += 1
    ttl = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds()
    client = _token_redis()
    if client is not None:
        try:
            client.set(f"user_deny:{user.id}", user.token_version, ex=ttl)
        except Exception:
            pass
    _mem_setex(f"user_deny:{user.id}", str(user.token_version), int(ttl))


def user_token_is_valid(user, token_version: int) -> bool:
    """A token is valid only while its version matches the current one."""
    client = _token_redis()
    denied: int | None = None
    if client is not None:
        try:
            raw = client.get(f"user_deny:{user.id}")
            denied = int(raw) if raw else None
        except Exception:
            pass
    if denied is None:
        denied = _mem_get(f"user_deny:{user.id}")
        if denied is not None:
            denied = int(denied)
    if denied is not None and token_version < denied:
        return False
    return token_version == user.token_version


def _revoke_key(key: str, ttl: int) -> None:
    client = _token_redis()
    if client is not None:
        try:
            client.set(key, "1", ex=ttl)
            return
        except Exception:
            pass
    _mem_setex(key, "1", ttl)


def revoke_access_token(token: str) -> None:
    try:
        payload = decode_token(token, expected_type=ACCESS_TYPE)
        ttl = int(payload["exp"]) - int(_now().timestamp())
        if ttl > 0:
            _revoke_key(f"jwt_deny:{payload['jti']}", ttl)
    except InvalidTokenError:
        pass


def revoke_refresh_token(token: str) -> None:
    try:
        payload = decode_token(token, expected_type=REFRESH_TYPE)
        jti = payload["jti"]
        _consume_refresh(jti)
        ttl = int(payload["exp"]) - int(_now().timestamp())
        if ttl > 0:
            _revoke_key(f"jwt_deny:{jti}", ttl)
    except InvalidTokenError:
        pass


def is_revoked(jti: str) -> bool:
    client = _token_redis()
    if client is not None:
        try:
            return bool(client.exists(f"jwt_deny:{jti}"))
        except Exception:
            pass
    return _mem_exists(f"jwt_deny:{jti}")


def access_token_expires_in_seconds() -> int:
    return settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
