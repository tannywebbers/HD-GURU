from __future__ import annotations

import threading
import time
from collections import defaultdict

from redis import Redis

from app.core.redis import redis_available

#: How long the DB-backed toggle result is cached before a re-read, so the
#: hot request path stays cheap while dashboard changes still take effect
#: within seconds.
_TOGGLE_CACHE_TTL = 5.0

_state_lock = threading.Lock()
_last_toggle_check = 0.0
_cached_enabled = True


def _read_toggle() -> bool:
    try:
        from app.core.config import settings
        from app.core.database import SessionLocal
        from app.services.settings_service import get_setting_bool

        with SessionLocal() as db:
            return get_setting_bool(
                db, "rate_limit.enabled", settings.RATE_LIMIT_ENABLED
            )
    except Exception:
        from app.core.config import settings

        return bool(settings.RATE_LIMIT_ENABLED)


def rate_limiting_enabled() -> bool:
    """Live, DB-backed rate-limiting master toggle.

    ``rate_limit.enabled`` (Admin -> Settings) is the source of truth; the
    env var only applies when the Setting row is absent. Cached for a few
    seconds so a dashboard change takes effect without a redeploy.
    """
    global _last_toggle_check, _cached_enabled
    now = time.time()
    if now - _last_toggle_check < _TOGGLE_CACHE_TTL:
        return _cached_enabled
    with _state_lock:
        now = time.time()
        if now - _last_toggle_check < _TOGGLE_CACHE_TTL:
            return _cached_enabled
        _last_toggle_check = now
        _cached_enabled = _read_toggle()
        return _cached_enabled


def reset_rate_limit_cache() -> None:
    """Drop the cached toggle so the next call re-reads the DB.

    Called by the test suite between isolated databases.
    """
    global _last_toggle_check, _cached_enabled
    with _state_lock:
        _last_toggle_check = 0.0
        _cached_enabled = True


class RateLimiter:
    """Sliding-window rate limiter backed by Redis with in-memory fallback."""

    def __init__(
        self,
        redis_client: Redis | None,
        *,
        enabled: bool = True,
        default_limit: int = 60,
        window_seconds: int = 60,
    ) -> None:
        self._redis = redis_client
        self.enabled = enabled
        self.default_limit = default_limit
        self.window = window_seconds
        self._mem: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int | None = None) -> bool:
        if not rate_limiting_enabled():
            return True

        limit = limit or self.default_limit
        now = time.time()

        if self._redis is not None and redis_available():
            try:
                rk = f"rl:{key}"
                pipe = self._redis.pipeline()
                pipe.zremrangebyscore(rk, 0, now - self.window)
                pipe.zadd(rk, {str(now): now})
                pipe.zcard(rk)
                pipe.expire(rk, self.window)
                _, _, count, _ = pipe.execute()
                return int(count) <= limit
            except Exception:
                # Redis hiccup -> fall back to the in-memory limiter.
                pass

        with self._lock:
            bucket = self._mem[key]
            cutoff = now - self.window
            while bucket and bucket[0] < cutoff:
                bucket.pop(0)
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True


_limiter: RateLimiter | None = None
_lock = threading.Lock()


def get_rate_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        with _lock:
            if _limiter is None:
                from app.core.config import settings
                from app.core.redis import get_redis

                _limiter = RateLimiter(
                    get_redis(),
                    enabled=settings.RATE_LIMIT_ENABLED,
                    default_limit=settings.RATE_LIMIT_DEFAULT_PER_MINUTE,
                )
    return _limiter
