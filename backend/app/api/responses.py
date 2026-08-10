from __future__ import annotations

from typing import Any

_AUTH_ERROR: dict[str, Any] = {
    "success": False,
    "error": {"code": "UNAUTHORIZED", "message": "Authentication is required."},
}
_FORBIDDEN_ERROR: dict[str, Any] = {
    "success": False,
    "error": {
        "code": "FORBIDDEN",
        "message": "You do not have permission to perform this action.",
    },
}
_NOT_FOUND_ERROR: dict[str, Any] = {
    "success": False,
    "error": {"code": "NOT_FOUND", "message": "Resource not found."},
}
_VALIDATION_ERROR: dict[str, Any] = {
    "success": False,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Request validation failed.",
        "details": [
            {"loc": ["body", "field"], "message": "Invalid value", "type": "value_error"}
        ],
    },
}
_RATE_LIMIT_ERROR: dict[str, Any] = {
    "success": False,
    "error": {
        "code": "RATE_LIMITED",
        "message": "Too many requests. Please try again later.",
    },
}
_INTERNAL_ERROR: dict[str, Any] = {
    "success": False,
    "error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."},
}


def error_response(code: str, message: str, details: Any = None) -> dict[str, Any]:
    body: dict[str, Any] = {"success": False, "error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return body


def auth_responses() -> dict[int, dict[str, Any]]:
    return {
        401: {"description": "Missing, invalid or expired credentials", "content": _json(_AUTH_ERROR)},
        403: {"description": "Forbidden", "content": _json(_FORBIDDEN_ERROR)},
        429: {"description": "Rate limited", "content": _json(_RATE_LIMIT_ERROR)},
        422: {"description": "Validation error", "content": _json(_VALIDATION_ERROR)},
    }


def standard_responses(
    extra: dict[int, dict[str, Any]] | None = None,
    **kwargs: dict[int, dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    base: dict[int, dict[str, Any]] = {
        401: {"description": "Unauthorized", "content": _json(_AUTH_ERROR)},
        403: {"description": "Forbidden", "content": _json(_FORBIDDEN_ERROR)},
        404: {"description": "Not found", "content": _json(_NOT_FOUND_ERROR)},
        422: {"description": "Validation error", "content": _json(_VALIDATION_ERROR)},
        429: {"description": "Rate limited", "content": _json(_RATE_LIMIT_ERROR)},
        500: {"description": "Internal error", "content": _json(_INTERNAL_ERROR)},
    }
    if extra:
        base.update(extra)
    base.update(kwargs)
    return base


def _json(example: Any) -> dict[str, Any]:
    return {"application/json": {"example": example}}
