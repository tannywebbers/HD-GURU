from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.rate_limit import RateLimiter, rate_limiting_enabled


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiting keyed by client IP + path."""

    def __init__(self, app, limiter: RateLimiter) -> None:
        super().__init__(app)
        self.limiter = limiter

    def _limit_for(self, method: str, path: str) -> int | None:
        if path.startswith("/api/v1/auth/login"):
            return settings.RATE_LIMIT_LOGIN_PER_MINUTE
        if method == "POST" and path.startswith("/api/v1/uploads"):
            return settings.RATE_LIMIT_UPLOAD_PER_MINUTE
        return None

    async def dispatch(self, request: Request, call_next):
        if not rate_limiting_enabled():
            return await call_next(request)

        # Meta can burst many events in a single retry wave; the webhook is
        # already gated by the X-Hub-Signature-256 validation, so per-IP
        # limiting would only 429 legitimate deliveries. Skip it here.
        if request.url.path.startswith("/api/v1/whatsapp/webhook"):
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        key = f"{client}:{request.url.path}"

        limit = self._limit_for(request.method, request.url.path)
        if not self.limiter.allow(key, limit=limit):
            return JSONResponse(
                status_code=429,
                content={
                    "detail": {
                        "code": "RATE_LIMITED",
                        "message": "Too many requests. Please try again later.",
                    }
                },
                headers={"Retry-After": str(self.limiter.window)},
            )
        return await call_next(request)
