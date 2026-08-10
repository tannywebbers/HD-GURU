from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import log
from app.models.enums import (
    MediaStatus,
    WhatsAppDeliveryStatus,
    WhatsAppEventStatus,
    WhatsAppMessageDirection,
    WhatsAppMessageStatus,
)
from app.models.media_file import MediaFile
from app.models.processed_media import ProcessedMedia
from app.models.upload import Upload
from app.models.whatsapp import (
    WhatsappContact,
    WhatsappMessage,
    WhatsappMessageStatus,
    WhatsappWebhookEvent,
)
from app.services.whatsapp import config as whatsapp_config
from app.services.whatsapp import media as media_service
from app.services.whatsapp import webhook as webhook_service
from app.services.whatsapp.client import WhatsAppGraphClient
from app.services.whatsapp.config import (
    EXPIRED_TEXT,
    FAILED_TEXT,
    HELP_TEXT,
    MEDIA_UNAVAILABLE_TEXT,
    NOT_FOUND_TEXT,
    NOT_READY_TEXT,
)
from app.services.whatsapp.errors import (
    WhatsAppConfigError,
    WhatsAppError,
    WhatsAppMediaError,
    WhatsAppValidationError,
)
from app.services.whatsapp.messages import (
    send_document_message,
    send_image_message,
    send_text_message,
    send_video_message,
)

_MAX_ERROR_LENGTH = 500


def persist_webhook_payload(db: Session, payload: dict) -> list[uuid.UUID]:
    """Persist normalized webhook events; returns their ids for the worker.

    The stored ``payload`` is the normalized event dict (meta_message_id,
    from_phone, text, meta, ...) so reprocessing is self-contained. The raw
    Meta payload is retained under ``raw`` for audit.
    """
    now = dt.datetime.now(dt.timezone.utc)
    event_ids: list[uuid.UUID] = []
    message_count = 0
    for event in webhook_service.iter_events(payload):
        row = WhatsappWebhookEvent(
            object=event.get("object"),
            entry_id=event.get("entry_id"),
            event_type=event.get("event_type", "unknown"),
            status=WhatsAppEventStatus.RECEIVED,
            payload=event,
            received_at=now,
        )
        db.add(row)
        db.flush()
        event_ids.append(row.id)
        if event.get("event_type") == "message":
            message_count += 1
    db.commit()
    if message_count:
        _track_whatsapp_messages(message_count)
    return event_ids


def _track_whatsapp_messages(count: int) -> None:
    """Best-effort analytics hook; never affects webhook processing."""
    try:
        from app.core.database import SessionLocal
        from app.services.analytics_service import track_event

        with SessionLocal() as db:
            for _ in range(count):
                track_event(
                    db,
                    event="whatsapp_message_received",
                    session_id=None,
                    page="/whatsapp",
                )
    except Exception:
        pass


def process_event(db: Session, event_id: uuid.UUID) -> dict:
    """Process a single persisted webhook event. Idempotent per event."""
    event = db.get(WhatsappWebhookEvent, event_id)
    if event is None:
        return {"status": "not_found"}
    if event.status == WhatsAppEventStatus.PROCESSED:
        return {"status": "already_processed"}

    cfg = whatsapp_config.load_config(db)
    if not cfg.enabled:
        event.status = WhatsAppEventStatus.IGNORED
        event.error = None
        db.commit()
        return {"status": "ignored_disabled"}

    try:
        if event.event_type == "message":
            _process_message(db, event, cfg)
        elif event.event_type == "status":
            _process_status(db, event)
        else:
            event.status = WhatsAppEventStatus.IGNORED
            db.commit()
            return {"status": "ignored_unknown"}
    except WhatsAppError as exc:
        db.rollback()
        if exc.retryable:
            log.warning(
                "whatsapp event transient failure",
                event_id=str(event.id),
                code=exc.code,
            )
            raise
        log.warning(
            "whatsapp event permanently failed",
            event_id=str(event.id),
            code=exc.code,
            error=exc.message,
        )
        event = db.get(WhatsappWebhookEvent, event_id)
        if event.event_type == "message":
            _fail_inbound_message(db, event, exc.code)
        event.status = WhatsAppEventStatus.FAILED
        event.error = exc.message[:_MAX_ERROR_LENGTH]
        event.processed_at = dt.datetime.now(dt.timezone.utc)
        db.commit()
        return {"status": "failed", "code": exc.code}

    event.status = WhatsAppEventStatus.PROCESSED
    event.error = None
    event.processed_at = dt.datetime.now(dt.timezone.utc)
    db.commit()
    return {"status": "processed", "event_type": event.event_type}


def _fail_inbound_message(db: Session, event: WhatsappWebhookEvent, code: str) -> None:
    meta_message_id = (
        event.payload.get("meta_message_id")
        if isinstance(event.payload, dict)
        else None
    )
    if not meta_message_id:
        return
    row = db.scalar(
        select(WhatsappMessage).where(
            WhatsappMessage.meta_message_id == meta_message_id,
            WhatsappMessage.direction == WhatsAppMessageDirection.INBOUND,
        )
    )
    if row is not None:
        row.status = WhatsAppMessageStatus.FAILED
        row.error_code = code


# --- message processing -----------------------------------------------------


def _process_message(db: Session, event: WhatsappWebhookEvent, cfg) -> None:
    payload = event.payload if isinstance(event.payload, dict) else {}
    meta_message_id = payload.get("meta_message_id")
    from_phone = payload.get("from_phone")
    text = payload.get("text")
    message_type = payload.get("message_type", "unknown")

    if not meta_message_id or not from_phone:
        raise WhatsAppValidationError("Webhook message is missing id or sender.")

    existing = db.scalar(
        select(WhatsappMessage).where(
            WhatsappMessage.meta_message_id == meta_message_id
        )
    )
    if existing is not None:
        log.info(
            "whatsapp duplicate message acknowledged",
            meta_message_id=meta_message_id,
        )
        return

    contact = _upsert_contact(db, from_phone, event)
    inbound = WhatsappMessage(
        meta_message_id=meta_message_id,
        direction=WhatsAppMessageDirection.INBOUND,
        contact_id=contact.id,
        message_type=message_type,
        text=text,
        status=WhatsAppMessageStatus.PROCESSING,
        timestamp=_event_datetime(event),
        meta={"source": "webhook"},
    )
    db.add(inbound)
    db.flush()

    media_public_id = webhook_service.extract_media_id(text)
    if not media_public_id:
        _reply_text(db, cfg, contact, HELP_TEXT, inbound, context=meta_message_id)
        return
    inbound.media_public_id = media_public_id

    media = db.scalar(
        select(MediaFile).where(
            func.lower(MediaFile.public_id) == media_public_id.lower()
        )
    )
    if media is None:
        _reply_text(db, cfg, contact, NOT_FOUND_TEXT, inbound, context=meta_message_id)
        return

    upload = db.get(Upload, media.upload_id)
    if upload is not None and upload.expires_at is not None:
        now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
        if upload.expires_at.replace(tzinfo=None) < now:
            _reply_text(db, cfg, contact, EXPIRED_TEXT, inbound, context=meta_message_id)
            return

    if media.status != MediaStatus.COMPLETED:
        if media.status == MediaStatus.FAILED:
            _reply_text(db, cfg, contact, FAILED_TEXT, inbound, context=meta_message_id)
        else:
            _reply_text(db, cfg, contact, NOT_READY_TEXT, inbound, context=meta_message_id)
        return

    processed = db.scalar(
        select(ProcessedMedia)
        .where(ProcessedMedia.media_file_id == media.id)
        .order_by(ProcessedMedia.created_at.desc())
        .limit(1)
    )
    if processed is None or processed.status != MediaStatus.COMPLETED:
        _reply_text(db, cfg, contact, NOT_READY_TEXT, inbound, context=meta_message_id)
        return

    _send_media_reply(db, cfg, contact, inbound, media, processed, meta_message_id)


def _send_media_reply(
    db: Session,
    cfg,
    contact: WhatsappContact,
    inbound: WhatsappMessage,
    media: MediaFile,
    processed: ProcessedMedia,
    context: str,
) -> None:
    mime = processed.mime_type
    caption = f"Here is your HD file for {media.public_id}"
    filename = processed.processed_filename or f"{media.public_id}.{processed.extension}"

    try:
        link = media_service.resolve_link_or_raise(db, processed, media)
    except WhatsAppMediaError as exc:
        log.warning("whatsapp media link unavailable", error=exc.message)
        _reply_text(db, cfg, contact, MEDIA_UNAVAILABLE_TEXT, inbound, context=context)
        inbound.status = WhatsAppMessageStatus.FAILED
        inbound.error_code = "WHATSAPP_MEDIA_ERROR"
        return

    client = _client(cfg)
    kind = media_service.send_type_for(mime)
    if kind == "image":
        result = send_image_message(client, contact.phone_number, link, caption=caption, context=context)
    elif kind == "video":
        result = send_video_message(client, contact.phone_number, link, caption=caption, context=context)
    else:
        result = send_document_message(client, contact.phone_number, link, filename=filename, caption=caption, context=context)

    message_id = result.get("message_id")
    _record_outbound(db, contact, media, mime, message_id)
    media.whatsapp_delivery_count += 1
    upload = db.get(Upload, media.upload_id)
    if upload is not None:
        upload.whatsapp_delivery_count += 1
    inbound.status = WhatsAppMessageStatus.SENT
    db.flush()
    log.info(
        "whatsapp media reply sent",
        media_public_id=media.public_id,
        kind=kind,
        message_id=message_id,
    )


def _reply_text(
    db: Session,
    cfg,
    contact: WhatsappContact,
    message: str,
    inbound: WhatsappMessage,
    *,
    context: str,
) -> None:
    client = _client(cfg)
    result = send_text_message(
        client, contact.phone_number, message, context=context
    )
    message_id = result.get("message_id")
    _record_outbound(
        db, contact, None, "text/plain", message_id, text=message
    )
    inbound.status = WhatsAppMessageStatus.SENT
    db.flush()


def _record_outbound(
    db: Session,
    contact: WhatsappContact,
    media: MediaFile | None,
    mime_type: str,
    message_id: str | None,
    *,
    text: str | None = None,
) -> None:
    outbound = WhatsappMessage(
        meta_message_id=message_id or f"out_{uuid.uuid4().hex}",
        direction=WhatsAppMessageDirection.OUTBOUND,
        contact_id=contact.id,
        message_type="text" if text else media_service.send_type_for(mime_type),
        text=text,
        media_public_id=media.public_id if media else None,
        status=(
            WhatsAppMessageStatus.SENT if message_id else WhatsAppMessageStatus.FAILED
        ),
        error_code=(
            None if message_id else "WHATSAPP_NO_MESSAGE_ID"
        ),
        timestamp=dt.datetime.now(dt.timezone.utc),
        meta={"media_mime_type": mime_type},
    )
    db.add(outbound)


def _client(cfg=None) -> WhatsAppGraphClient:
    config = cfg or whatsapp_config.load_config()
    try:
        return WhatsAppGraphClient(config)
    except WhatsAppConfigError:
        raise WhatsAppConfigError(
            "WhatsApp is not fully configured (missing token or phone number id)."
        ) from None


def _upsert_contact(
    db: Session, phone: str, event: WhatsappWebhookEvent
) -> WhatsappContact:
    now = dt.datetime.now(dt.timezone.utc)
    meta = event.payload.get("meta") if isinstance(event.payload, dict) else None
    meta = meta or {}
    wa_id = meta.get("wa_id")
    display_name = meta.get("display_name")

    contact = db.scalar(
        select(WhatsappContact).where(WhatsappContact.phone_number == phone)
    )
    if contact is None:
        contact = WhatsappContact(
            wa_id=wa_id or phone,
            phone_number=phone,
            display_name=display_name,
            first_seen=now,
            last_seen=now,
        )
        db.add(contact)
    else:
        if wa_id and contact.wa_id != wa_id:
            contact.wa_id = wa_id
        if display_name:
            contact.display_name = display_name
        contact.last_seen = now
    db.flush()
    return contact


def _event_datetime(event: WhatsappWebhookEvent) -> dt.datetime | None:
    payload = event.payload if isinstance(event.payload, dict) else {}
    ts = payload.get("timestamp")
    if isinstance(ts, (int, float)) and ts > 0:
        try:
            return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    return None


# --- delivery status handling -----------------------------------------------


def _process_status(db: Session, event: WhatsappWebhookEvent) -> None:
    payload = event.payload if isinstance(event.payload, dict) else {}
    meta_message_id = payload.get("meta_message_id")
    status = payload.get("delivery_status")
    if not meta_message_id or not status:
        raise WhatsAppValidationError("Status event is missing id or status.")

    try:
        delivery = WhatsAppDeliveryStatus(status)
    except ValueError:
        log.info(
            "whatsapp unknown delivery status",
            status=status,
        )
        return

    message = db.scalar(
        select(WhatsappMessage).where(
            WhatsappMessage.meta_message_id == meta_message_id
        )
    )
    row = WhatsappMessageStatus(
        message_id=message.id if message else None,
        meta_message_id=meta_message_id,
        status=delivery,
        timestamp=_event_datetime(event),
        meta=payload,
    )
    db.add(row)
    if message is not None:
        if delivery == WhatsAppDeliveryStatus.FAILED:
            message.status = WhatsAppMessageStatus.FAILED
            message.error_code = "WHATSAPP_DELIVERY_FAILED"
        elif message.status != WhatsAppMessageStatus.FAILED:
            message.status = WhatsAppMessageStatus.SENT
    db.flush()
    log.info(
        "whatsapp delivery status",
        meta_message_id=meta_message_id,
        status=status,
    )


# --- connection test + status ------------------------------------------------


def test_connection(db: Session) -> dict:
    """Verify configured Meta credentials against the phone number id."""
    cfg = whatsapp_config.load_config(db)
    if not cfg.access_token or not cfg.phone_number_id:
        return {
            "success": False,
            "message": "Configure an access token and phone number ID first.",
        }
    try:
        client = _client(cfg)
    except WhatsAppConfigError as exc:
        return {"success": False, "message": exc.message}
    return client.test_credentials()


def webhook_status(db: Session) -> dict:
    """Health/status report for the webhook + integration."""
    cfg = whatsapp_config.load_config(db)
    last_event = db.scalar(
        select(WhatsappWebhookEvent).order_by(
            WhatsappWebhookEvent.received_at.desc()
        ).limit(1)
    )
    last_error = db.scalar(
        select(WhatsappWebhookEvent)
        .where(WhatsappWebhookEvent.status == WhatsAppEventStatus.FAILED)
        .order_by(WhatsappWebhookEvent.received_at.desc())
        .limit(1)
    )
    last_message = db.scalar(
        select(WhatsappMessage).order_by(
            WhatsappMessage.timestamp.desc()
        ).limit(1)
    )
    return {
        "enabled": cfg.enabled,
        "credentials_configured": bool(cfg.access_token),
        "phone_number_id_configured": bool(cfg.phone_number_id),
        "webhook_configured": cfg.has_webhook_credentials(),
        "webhook_endpoint": "/api/v1/whatsapp/webhook",
        "api_version": cfg.api_version,
        "last_webhook_received_at": last_event.received_at if last_event else None,
        "last_webhook_event_type": last_event.event_type if last_event else None,
        "last_webhook_error": last_error.error if last_error else None,
        "last_message_at": last_message.timestamp if last_message else None,
    }


def mark_event_failed(db: Session, event_id: uuid.UUID, error: str) -> None:
    """Final failure marker used by the worker after retries are exhausted."""
    event = db.get(WhatsappWebhookEvent, event_id)
    if event is None:
        return
    event.status = WhatsAppEventStatus.FAILED
    event.error = error[:_MAX_ERROR_LENGTH]
    event.processed_at = dt.datetime.now(dt.timezone.utc)
    db.commit()
