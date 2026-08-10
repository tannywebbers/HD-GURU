from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.api.responses import standard_responses
from app.core.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.settings import (
    PublicBrandingOut,
    SettingsOut,
    SettingsUpdateRequest,
)
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get(
    "/public",
    response_model=PublicBrandingOut,
    summary="Public branding configuration",
    description=(
        "Safe branding values for the public frontend and PWA manifest: app "
        "name, description, optional logo/theme/primary colour. No secrets and "
        "no admin-only settings are ever included; HD Guru defaults are used "
        "when branding has not been configured."
    ),
    responses=standard_responses(),
)
def get_public_branding(db: Session = Depends(get_db)) -> PublicBrandingOut:
    return PublicBrandingOut(**settings_service.public_branding(db))


@router.get(
    "",
    response_model=SettingsOut,
    summary="List application settings",
    description=(
        "Returns all settings. Secret values are masked for non-admin users. "
        "Requires authentication."
    ),
    responses=standard_responses(),
)
def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SettingsOut:
    is_admin = current_user.role == UserRole.ADMIN
    return settings_service.list_settings(db, is_admin=is_admin)


@router.put(
    "",
    response_model=SettingsOut,
    summary="Update settings (admin only)",
    description=(
        "Updates the given settings. Every change is recorded in the audit "
        "log with the acting admin, IP and user agent."
    ),
    responses=standard_responses(),
)
def update_settings(
    payload: SettingsUpdateRequest,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> SettingsOut:
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return settings_service.update_settings(
        db,
        payload.settings,
        actor=current_user,
        ip_address=ip_address,
        user_agent=user_agent,
    )
