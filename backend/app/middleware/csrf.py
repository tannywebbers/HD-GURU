from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from urllib.parse import urlparse

from app.core.config import settings

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """Origin validation for state-changing requests.

    The API authenticates with Bearer tokens (not cookies), so classic CSRF is
    largely theoretical. This middleware hardens the surface anyway: for
    unsafe methods it requires an ``Origin`` (or ``Referer``) header that
    matches one of the allowed hosts, unless CORS is wide open (``*``) which
    means same-origin is the only thing that matters.

    Requests without an Origin header (server-to-server clients) pass through.
    """

    async def dispatch(self, request: Request, call_next):
        if request.method in _SAFE_METHODS or not settings.CSRF_PROTECTION_ENABLED:
            return await call_next(request)

        allowed_hosts = settings.allowed_hosts_list
        # "*" disables host pinning entirely.
        if "*" in allowed_hosts:
            return await call_next(request)

        origin = request.headers.get("origin")
        referer = request.headers.get("referer")
        source = None
        if origin:
            source = origin
        elif referer:
            parsed = urlparse(referer)
            source = f"{parsed.scheme}://{parsed.netloc}"

        # No origin info: treat as a non-browser client and allow.
        if source is None:
            return await call_next(request)

        host = urlparse(source).netloc
        if not _host_allowed(host, allowed_hosts):
            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "error": {
                        "code": "CSRF_FAILED",
                        "message": "Origin is not allowed.",
                    },
                },
            )
        return await call_next(request)


def _host_allowed(host: str, allowed_hosts: list[str]) -> bool:
    if not host:
        return False
    if "*" in allowed_hosts:
        return True
    for allowed in allowed_hosts:
        if allowed.startswith("*."):
            base = allowed[2:]
            if host == base or host.endswith(f".{base}"):
                return True
        elif host == allowed:
            return True
    return False
