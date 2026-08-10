from __future__ import annotations

from app.models.enums import Permission, UserRole

_ALL_PERMISSIONS = frozenset(Permission)

# Every role may operate at or above its own level (super_admin grants admin,
# admin grants operator, operator grants viewer). A user role has no admin
# access at all.
_ROLE_LEVEL: dict[UserRole, int] = {
    UserRole.USER: 0,
    UserRole.VIEWER: 1,
    UserRole.OPERATOR: 2,
    UserRole.ADMIN: 3,
    UserRole.SUPER_ADMIN: 4,
}

# Base grant per role level. Higher levels inherit every permission granted to
# lower levels (e.g. operator inherits the viewer read-only set).
_LEVEL_PERMISSIONS: dict[int, frozenset[Permission]] = {
    1: frozenset(
        {
            Permission.DASHBOARD_VIEW,
            Permission.MEDIA_VIEW,
            Permission.JOBS_VIEW,
            Permission.USERS_VIEW,
            Permission.WHATSAPP_VIEW,
            Permission.WATERMARK_VIEW,
            Permission.STORAGE_VIEW,
            Permission.SETTINGS_VIEW,
            Permission.SECURITY_VIEW,
            Permission.LOGS_VIEW,
            Permission.AUDIT_VIEW,
            Permission.HEALTH_VIEW,
            Permission.ADS_VIEW,
            Permission.ANALYTICS_VIEW,
        }
    ),
    2: frozenset(
        {
            Permission.MEDIA_DELETE,
            Permission.JOBS_RETRY,
            Permission.WHATSAPP_MANAGE,
            Permission.WHATSAPP_TEST,
            Permission.WATERMARK_MANAGE,
        }
    ),
    3: frozenset(
        {
            Permission.USERS_MANAGE,
            Permission.WHATSAPP_CREDENTIALS,
            Permission.SETTINGS_MANAGE,
            Permission.SECURITY_MANAGE,
            Permission.ADS_MANAGE,
        }
    ),
    4: frozenset(_ALL_PERMISSIONS),
}


def role_level(role: UserRole) -> int:
    return _ROLE_LEVEL.get(role, 0)


def has_permission(role: UserRole, permission: Permission) -> bool:
    """True when ``role`` (or a higher role) is granted ``permission``."""
    level = role_level(role)
    for candidate_level in range(level, 0, -1):
        if permission in _LEVEL_PERMISSIONS[candidate_level]:
            return True
    return False


def role_permissions(role: UserRole) -> list[str]:
    """Expose the effective permission list for the current admin user.

    Lets the frontend hide actions without ever being the security boundary.
    """
    level = role_level(role)
    granted: set[Permission] = set()
    for candidate_level in range(level, 0, -1):
        granted.update(_LEVEL_PERMISSIONS[candidate_level])
    return sorted(p.value for p in granted)
