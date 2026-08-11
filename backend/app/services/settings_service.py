from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.setting import Setting
from app.models.user import User
from app.repositories.settings import SettingRepository
from app.schemas.settings import (
    SettingItem,
    SettingsItemUpdate,
    SettingsOut,
)
from app.services import audit_service

#: Sentinel the admin dashboard sends back for a secret it did not change.
MASKED_VALUE = "***"

_TRUE_VALUES = {"true", "1", "yes", "on"}
_FALSE_VALUES = {"false", "0", "no", "off"}


def get_setting_value(db: Session, key: str, default=None):
    """Return a setting's stored value, or ``default`` when the key is absent.

    The live source of truth for runtime configuration. Environment variables
    are only fallbacks supplied by callers as ``default``.
    """
    row = SettingRepository(db).get_by_key(key)
    return default if row is None else row.value


def get_setting_bool(db: Session, key: str, default: bool = False) -> bool:
    """Coerce a setting to bool, accepting JSON booleans and string literals.

    Handles the classic ``bool("false") is True`` pitfall: "true"/"1"/"yes"/"on"
    (any case) are True, "false"/"0"/"no"/"off" are False, anything else falls
    back to ``default``.
    """
    value = get_setting_value(db, key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        text = value.strip().lower()
        if text in _TRUE_VALUES:
            return True
        if text in _FALSE_VALUES:
            return False
    return bool(default)


def get_setting_int(db: Session, key: str, default: int = 0) -> int:
    """Coerce a setting to int; unparseable values fall back to ``default``."""
    value = get_setting_value(db, key, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def list_settings(db: Session, *, is_admin: bool) -> SettingsOut:
    rows = SettingRepository(db).all()
    items: list[SettingItem] = []
    for row in rows:
        value = row.value
        if row.is_secret and not is_admin:
            value = "***"
        items.append(
            SettingItem(
                key=row.key,
                group=row.group,
                value=value,
                description=row.description,
                is_secret=row.is_secret,
                updated_at=row.updated_at,
            )
        )
    return SettingsOut(settings=items)


def update_settings(
    db: Session,
    payload: list[SettingsItemUpdate],
    *,
    actor: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> SettingsOut:
    repo = SettingRepository(db)
    updated_keys: list[str] = []
    for item in payload:
        row = repo.get_by_key(item.key)
        if row is None:
            raise AppError(
                404, "SETTING_NOT_FOUND", f"Unknown setting '{item.key}'."
            )
        if row.is_secret and item.value == MASKED_VALUE:
            # The dashboard echoes '***' for secrets it did not change; leave
            # the stored value untouched instead of writing the sentinel.
            continue
        row.value = item.value
        updated_keys.append(item.key)
    audit_service.log_action(
        db,
        action=audit_service.ACTION_SETTINGS_UPDATE,
        actor=actor,
        resource_type="settings",
        details={"keys": updated_keys},
        ip_address=ip_address,
        user_agent=user_agent,
        commit=False,
    )
    db.commit()
    return list_settings(db, is_admin=True)


def count_settings(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Setting)) or 0


_BRANDING_DEFAULTS: dict[str, str] = {
    "app.name": "HD Guru",
    "app.description": (
        "Transform your photos and videos into stunning HD quality in seconds. "
        "Free, private, and delivered straight to WhatsApp."
    ),
}


def public_branding(db: Session) -> dict:
    """Public branding payload — non-secret settings with HD Guru fallbacks.

    This is the single source of truth for the public app name/description
    (Admin → Settings → ``app.*``). Logo/theme/primary colour are optional:
    when unset they come back as ``None`` and the frontend keeps its defaults.
    """
    rows = {row.key: row.value for row in SettingRepository(db).all()}
    return {
        "app_name": rows.get("app.name") or _BRANDING_DEFAULTS["app.name"],
        "app_description": (
            rows.get("app.description") or _BRANDING_DEFAULTS["app.description"]
        ),
        "app_logo_url": rows.get("app.logo_url") or None,
        "app_theme_color": rows.get("app.theme_color") or None,
        "app_primary_color": rows.get("app.primary_color") or None,
    }
