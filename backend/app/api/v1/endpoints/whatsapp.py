from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from app.api.deps import require_roles
from app.api.responses import standard_responses
from app.core.database import get_db
from app.core.logging import log
from app.models.enums import WhatsAppEventStatus, UserRole
from app.models.whatsapp import WhatsappWebhookEvent
from app.schemas.whatsapp import WhatsAppConfigUpdate
from app.services import audit_service
from app.services.whatsapp import config as whatsapp_config
from app.services.whatsapp import service as whatsapp_service
from app.services.whatsapp import webhook as webhook_service
from app.services.whatsapp.errors import WhatsAppWebhookError
from app.workers.tasks import process_whatsapp_event

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])
public_router = APIRouter(prefix="/public", tags=["Public"])


# --- webhook ----------------------------------------------------------------


@router.get(
    "/webhook",
    response_model=None,
    include_in_schema=False,
    summary="Meta webhook verification handshake",
    description=(
        "Called by Meta when the callback URL is registered. Returns the "
        "challenge only when the token matches; anything else answers 403."
    ),
)
def verify_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
    db: Session = Depends(get_db),
):
    cfg = whatsapp_config.load_config(db)
    try:
        challenge = webhook_service.verify_challenge(
            hub_mode, hub_verify_token, hub_challenge, cfg
        )
    except WhatsAppWebhookError as exc:
        log.warning("whatsapp webhook verification rejected")
        raise HTTPException(status_code=exc.http_status or 403) from None
    return PlainTextResponse(challenge)


@router.post(
    "/webhook",
    response_model=None,
    include_in_schema=False,
    summary="Receive WhatsApp webhook events",
    description=(
        "Validates the X-Hub-Signature-256 header, acknowledges immediately "
        "and queues each event for background processing."
    ),
)
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    cfg = whatsapp_config.load_config(db)
    signature = request.headers.get("x-hub-signature-256")
    if not webhook_service.is_valid_signature(body, signature, cfg.app_secret):
        log.warning("whatsapp webhook signature invalid")
        raise HTTPException(status_code=403, detail="Invalid signature.")

    try:
        payload = json.loads(body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        log.warning("whatsapp webhook payload not json")
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload.")

    event_ids = whatsapp_service.persist_webhook_payload(db, payload)
    if event_ids and cfg.enabled and cfg.is_fully_configured():
        for event_id in event_ids:
            try:
                process_whatsapp_event.delay(str(event_id))
            except Exception as exc:  # broker/eager failures must not break the ack
                log.exception(
                    "failed to enqueue whatsapp event",
                    event_id=str(event_id),
                    error=str(exc),
                )
    elif event_ids:
        _mark_ignored(db, event_ids)
    log.info("whatsapp webhook received", events=len(event_ids))
    return {"status": "ok", "events": len(event_ids)}


def _mark_ignored(db: Session, event_ids: list) -> None:
    from sqlalchemy import update

    db.execute(
        update(WhatsappWebhookEvent)
        .where(WhatsappWebhookEvent.id.in_(event_ids))
        .values(status=WhatsAppEventStatus.IGNORED)
    )
    db.commit()


# --- configuration (admin) ---------------------------------------------------


@router.get(
    "/config",
    summary="WhatsApp configuration status (admin only)",
    description=(
        "Returns the effective configuration with secrets masked. Never "
        "returns tokens, verify tokens or app secrets."
    ),
    responses=standard_responses(),
)
def get_whatsapp_config(
    current_user=Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    return whatsapp_config.config_status(db)


@router.put(
    "/config",
    summary="Update WhatsApp configuration (admin only)",
    description=(
        "Updates the persisted WhatsApp settings row. Only the provided "
        "fields are changed; secrets are never echoed back."
    ),
    responses=standard_responses(),
)
def update_whatsapp_config(
    payload: WhatsAppConfigUpdate,
    request: Request,
    current_user=Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    kwargs = payload.model_dump(exclude_none=True)
    row = whatsapp_config.upsert_config(db, **kwargs)
    ip, user_agent = audit_service.client_meta(request)
    audit_service.log_action(
        db,
        action="whatsapp.config_updated",
        actor=current_user,
        resource_type="whatsapp_setting",
        resource_id=str(row.id),
        details={"fields": sorted(kwargs.keys())},
        ip_address=ip,
        user_agent=user_agent,
    )
    return whatsapp_config.config_status(db)


@router.post(
    "/config/test",
    summary="Test the WhatsApp connection (admin only)",
    description=(
        "Verifies the configured access token and phone number ID against the "
        "Graph API. Returns a safe result without any credentials."
    ),
    responses=standard_responses(),
)
def test_whatsapp_connection(
    current_user=Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    return whatsapp_service.test_connection(db)


@router.get(
    "/webhook/status",
    summary="WhatsApp webhook status (admin only)",
    description=(
        "Health report: enabled state, whether webhook credentials are "
        "configured, and the last received/processed/failed events."
    ),
    responses=standard_responses(),
)
def whatsapp_webhook_status(
    current_user=Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    return whatsapp_service.webhook_status(db)


# --- public ----------------------------------------------------------------


@public_router.get(
    "/whatsapp",
    summary="Public WhatsApp availability",
    description=(
        "Safe values the frontend needs to build the wa.me link: enabled "
        "state, display phone number and the message template. No ids, no "
        "secrets."
    ),
    responses=standard_responses(),
)
def public_whatsapp_config(db: Session = Depends(get_db)):
    return whatsapp_config.public_config(db)
