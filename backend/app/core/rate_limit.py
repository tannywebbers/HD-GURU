from __future__ import annotations

import threading
import time
from collections import defaultdict

from redis import Redis

from app.core.redis import redis_available


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
        if not self.enabled:
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
