from __future__ import annotations

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import settings


class SecurityHeadersMiddleware:
    """Add hardened HTTP response headers to every response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-Frame-Options"] = "DENY"
                headers["Referrer-Policy"] = "no-referrer"
                headers["Permissions-Policy"] = (
                    "geolocation=(), microphone=(), camera=()"
                )
                headers["Content-Security-Policy"] = (
                    "default-src 'self'; script-src 'self'; "
                    "style-src 'self' 'unsafe-inline'; "
                    "img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'"
                )
                headers["Cross-Origin-Opener-Policy"] = "same-origin"
                headers["Cross-Origin-Resource-Policy"] = "same-origin"
                headers["X-DNS-Prefetch-Control"] = "off"
                headers["Cache-Control"] = "no-store"
                if settings.ENVIRONMENT != "development":
                    headers["Strict-Transport-Security"] = (
                        f"max-age={settings.HSTS_MAX_AGE}; includeSubDomains"
                    )
            await send(message)

        await self.app(scope, receive, send_wrapper)
