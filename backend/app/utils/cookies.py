from __future__ import annotations

import datetime as dt

from fastapi import Response

from app.core.config import settings


def secure_cookie_params(
    *, path: str = "/", max_age: int | None = None
) -> dict:
    """Standard attributes for an authentication cookie.

    Cookies are used only as an alternative transport for the same tokens the
    API already exchanges via headers; the backend never *requires* a cookie.
    """
    params: dict = {
        "path": path,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
        "httponly": True,
    }
    if max_age is not None:
        params["max_age"] = max_age
    return params


def set_access_cookie(
    response: Response, token: str, expires_in: int
) -> None:
    response.set_cookie(
        settings.COOKIE_NAME_ACCESS,
        token,
        **secure_cookie_params(max_age=expires_in),
    )


def set_refresh_cookie(
    response: Response, token: str, expires_in_days: int
) -> None:
    response.set_cookie(
        settings.COOKIE_NAME_REFRESH,
        token,
        **secure_cookie_params(max_age=expires_in_days * 86400),
    )


def clear_auth_cookies(response: Response) -> None:
    for name in (settings.COOKIE_NAME_ACCESS, settings.COOKIE_NAME_REFRESH):
        response.delete_cookie(name, **secure_cookie_params())


def cookie_expires_in_days(days: int) -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=days)
