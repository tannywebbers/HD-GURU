from __future__ import annotations

import uuid

from fastapi import Depends, Header
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.permissions import has_permission, role_level
from app.core.security import decode_token, is_revoked, user_token_is_valid
from app.models.enums import Permission, UserRole
from app.models.user import User


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> User:
    token = _extract_bearer(authorization)
    if token is None:
        raise AppError(401, "UNAUTHORIZED", "Authentication is required.")

    payload = _decode_access(token)
    user = db.get(User, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise AppError(401, "UNAUTHORIZED", "User is inactive or missing.")
    if not user_token_is_valid(user, int(payload.get("tver", 0))):
        raise AppError(
            401, "TOKEN_STALE", "Tokens have been revoked. Please log in again."
        )
    return user


def get_current_user_optional(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> User | None:
    token = _extract_bearer(authorization)
    if token is None:
        return None
    try:
        payload = _decode_access(token)
        user = db.get(User, uuid.UUID(payload["sub"]))
    except AppError:
        return None
    if user is None or not user.is_active:
        return None
    if not user_token_is_valid(user, int(payload.get("tver", 0))):
        return None
    return user


def require_roles(*roles: UserRole):
    """Role gate using the role hierarchy (super_admin > admin > operator > viewer).

    A caller is admitted when their role level is at least the lowest of the
    requested roles, so e.g. ``require_roles(UserRole.ADMIN)`` also admits
    ``SUPER_ADMIN``. This keeps admin-panel endpoints reachable for
    super-admins instead of locking them out with an exact-match check.
    """
    min_level = min(role_level(r) for r in roles)

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if role_level(current_user.role) < min_level:
            raise AppError(
                403,
                "FORBIDDEN",
                "You do not have permission to perform this action.",
            )
        return current_user

    return dependency


def require_admin(
    min_role: UserRole = UserRole.VIEWER,
    permission: Permission | None = None,
):
    """Admin-only dependency with hierarchical role checks.

    ``min_role`` gates on role level (super_admin > admin > operator > viewer).
    ``permission`` additionally requires a specific permission. Admins always
    satisfy the permission for their own level and every level below it.
    """

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if role_level(current_user.role) < role_level(min_role):
            raise AppError(
                403,
                "FORBIDDEN",
                "You do not have permission to perform this action.",
            )
        if permission is not None and not has_permission(
            current_user.role, permission
        ):
            raise AppError(
                403,
                "FORBIDDEN",
                "You do not have permission to perform this action.",
            )
        return current_user

    return dependency


def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AppError(401, "UNAUTHORIZED", "Invalid authorization header.")
    return token


def _decode_access(token: str) -> dict:
    try:
        payload = decode_token(token, expected_type="access")
    except InvalidTokenError:
        raise AppError(401, "UNAUTHORIZED", "Invalid or expired token.") from None
    if is_revoked(payload["jti"]):
        raise AppError(401, "UNAUTHORIZED", "Token has been revoked.")
    return payload
