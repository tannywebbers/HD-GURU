from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.whatsapp_setting import WhatsappSetting

SETTING_NAME = "primary"

#: Sentinel the admin dashboard sends back for a secret it did not change.
UNCHANGED = "***"

# Friendly default responses. Wording lives here so the API layer stays thin.
HELP_TEXT = (
    "To get your HD file, send the HD ID that appears after processing, "
    "like this:\nSend HD for ABC123XYZ789ABC"
)
NOT_FOUND_TEXT = (
    "We couldn't find that HD media. Please check the ID and try again."
)
NOT_READY_TEXT = (
    "Your HD file is still being prepared. Please wait a moment and try again."
)
EXPIRED_TEXT = (
    "Sorry, that HD media has expired. Please upload your files again to get a "
    "new HD version."
)
FAILED_TEXT = (
    "Sorry, that HD media could not be processed. Please try uploading it again."
)
MEDIA_UNAVAILABLE_TEXT = (
    "Sorry, we can't send that file right now. Please try again in a moment."
)


@dataclass
class WhatsAppConfig:
    enabled: bool
    access_token: str
    phone_number_id: str
    phone_number: str
    business_account_id: str
    verify_token: str
    app_secret: str
    api_version: str
    graph_api_base_url: str

    def graph_base(self) -> str:
        return f"{self.graph_api_base_url.rstrip('/')}/{self.api_version}"

    def messaging_endpoint(self) -> str:
        return f"{self.graph_base()}/{self.phone_number_id}/messages"

    def media_endpoint(self) -> str:
        return f"{self.graph_base()}/{self.phone_number_id}/media"

    def is_fully_configured(self) -> bool:
        """True when the integration can actually send messages."""
        return bool(
            self.enabled
            and self.access_token
            and self.phone_number_id
            and self.api_version
        )

    def has_webhook_credentials(self) -> bool:
        return bool(self.verify_token and self.app_secret)


def _pick(row_value, env_value):
    if row_value not in (None, ""):
        return row_value
    return env_value


def load_config(db: Session | None = None) -> WhatsAppConfig:
    """Resolve the effective WhatsApp configuration.

    Values stored on the ``WhatsappSetting`` row (admin-editable via the API)
    take precedence over environment variables; environment variables provide
    the defaults. Secrets are never exposed to clients.
    """
    row: WhatsappSetting | None = None
    if db is not None:
        row = db.scalar(
            select(WhatsappSetting).where(WhatsappSetting.name == SETTING_NAME)
        )
    enabled = row.enabled if row is not None else settings.WHATSAPP_ENABLED
    return WhatsAppConfig(
        enabled=enabled,
        access_token=_pick(row.access_token if row else None, settings.WHATSAPP_ACCESS_TOKEN),
        phone_number_id=_pick(
            row.phone_number_id if row else None, settings.WHATSAPP_PHONE_NUMBER_ID
        ),
        phone_number=_pick(
            row.phone_number if row else None, settings.WHATSAPP_PHONE_NUMBER
        ),
        business_account_id=_pick(
            row.business_account_id if row else None,
            settings.WHATSAPP_BUSINESS_ACCOUNT_ID,
        ),
        verify_token=_pick(
            row.webhook_verify_token if row else None, settings.WHATSAPP_VERIFY_TOKEN
        ),
        app_secret=_pick(
            row.webhook_secret if row else None, settings.WHATSAPP_APP_SECRET
        ),
        api_version=_pick(
            row.api_version if row else None, settings.WHATSAPP_GRAPH_API_VERSION
        ),
        graph_api_base_url=_pick(
            row.graph_api_base_url if row else None,
            settings.WHATSAPP_GRAPH_API_BASE_URL,
        ),
    )


def upsert_config(
    db: Session,
    *,
    enabled: bool | None = None,
    phone_number_id: str | None = None,
    phone_number: str | None = None,
    business_account_id: str | None = None,
    access_token: str | None = None,
    verify_token: str | None = None,
    app_secret: str | None = None,
    api_version: str | None = None,
    graph_api_base_url: str | None = None,
) -> WhatsappSetting:
    """Create or update the persisted WhatsApp configuration row."""
    row = db.scalar(
        select(WhatsappSetting).where(WhatsappSetting.name == SETTING_NAME)
    )
    if row is None:
        row = WhatsappSetting(name=SETTING_NAME, enabled=False)
        db.add(row)

    if enabled is not None:
        row.enabled = enabled
    if phone_number_id is not None:
        row.phone_number_id = phone_number_id
    if phone_number is not None:
        row.phone_number = phone_number
    if business_account_id is not None:
        row.business_account_id = business_account_id
    if access_token is not None and access_token != UNCHANGED:
        row.access_token = access_token
    if verify_token is not None and verify_token != UNCHANGED:
        row.webhook_verify_token = verify_token
    if app_secret is not None and app_secret != UNCHANGED:
        row.webhook_secret = app_secret
    if api_version is not None:
        row.api_version = api_version
    if graph_api_base_url is not None:
        row.graph_api_base_url = graph_api_base_url
    db.commit()
    db.refresh(row)
    return row


def mask_secret(value: str | None, keep: int = 4) -> str | None:
    """Mask a token for display: keep first+last chars, replace the middle."""
    if not value:
        return None
    if len(value) <= keep * 2:
        return "***"
    return f"{value[:keep]}...{value[-keep:]}"


def config_status(db: Session) -> dict:
    """Safe configuration status. Never includes secrets, only masked hints."""
    cfg = load_config(db)
    return {
        "enabled": cfg.enabled,
        "phone_number_id": cfg.phone_number_id or None,
        "phone_number": cfg.phone_number or None,
        "business_account_id": cfg.business_account_id or None,
        "api_version": cfg.api_version,
        "graph_api_base_url": cfg.graph_api_base_url or None,
        "token_configured": bool(cfg.access_token),
        "verify_token_configured": bool(cfg.verify_token),
        "app_secret_configured": bool(cfg.app_secret),
        "access_token_masked": mask_secret(cfg.access_token),
        "verify_token_masked": mask_secret(cfg.verify_token),
        "app_secret_masked": mask_secret(cfg.app_secret),
        "connected": cfg.is_fully_configured(),
    }


def public_config(db: Session | None = None) -> dict:
    """Safe values for the frontend (no secrets, no ids)."""
    cfg = load_config(db)
    return {
        "enabled": cfg.enabled,
        "phone_number": cfg.phone_number or None,
        "message_template": "Send HD for {ID}",
    }


def build_whatsapp_link(public_id: str, db: Session | None = None) -> str | None:
    """Build the click-to-chat wa.me URL for a completed HD ID.

    Uses the effective configuration (DB row when available, else env). The
    prefilled message is exactly ``Send HD for {public_id}`` so the webhook
    parser recognises it and can deliver the file.
    """
    from urllib.parse import quote

    cfg = load_config(db)
    if not cfg.enabled or not cfg.phone_number:
        return None
    digits = "".join(ch for ch in cfg.phone_number if ch.isdigit())
    text = f"Send HD for {public_id}"
    return f"https://wa.me/{digits}?text={quote(text)}"
