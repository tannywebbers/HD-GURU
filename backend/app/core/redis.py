from __future__ import annotations

import time

import redis
from redis import Redis

from app.core.config import settings

_client: Redis | None = None
_available: bool | None = None
_last_check = 0.0
_CHECK_INTERVAL = 30.0


def get_redis() -> Redis:
    """Return a lazily created Redis client."""
    global _client
    if _client is None:
        _client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            health_check_interval=30,
        )
    return _client


def redis_available() -> bool:
    """Cached connectivity probe so downed Redis doesn't stall every call."""
    global _available, _last_check
    now = time.monotonic()
    if _available is None or now - _last_check > _CHECK_INTERVAL:
        try:
            get_redis().ping()
            _available = True
        except Exception:
            _available = False
        _last_check = now
    return _available


def ping_redis() -> bool:
    return redis_available()


def close_redis() -> None:
    global _client
    if _client is not None:
        try:
            _client.close()
        finally:
            _client = None
