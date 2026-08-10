from __future__ import annotations

import hashlib
import hmac
import re

from app.services.whatsapp.config import WhatsAppConfig
from app.services.whatsapp.errors import WhatsAppWebhookError

_HD_ID_PHRASE = re.compile(
    r"(?:send\s*hd\s*for\s*:?)\s*([A-Za-z0-9]{16})\b", re.IGNORECASE
)
_HD_ID_TOKEN = re.compile(r"\b([A-Za-z0-9]{16})\b")


def verify_challenge(
    mode: str | None,
    token: str | None,
    challenge: str | None,
    config: WhatsAppConfig,
) -> str:
    """Meta webhook verification handshake.

    Returns the challenge only when the mode is ``subscribe`` and the token
    matches (constant-time compare). Raises otherwise.
    """
    if mode != "subscribe":
        raise WhatsAppWebhookError("Webhook verification failed.", http_status=403)
    if not config.verify_token:
        raise WhatsAppWebhookError(
            "Webhook verify token is not configured.", http_status=403
        )
    if not challenge or not token or not hmac.compare_digest(token, config.verify_token):
        raise WhatsAppWebhookError("Webhook verification failed.", http_status=403)
    return challenge


def is_valid_signature(
    payload: bytes, header: str | None, app_secret: str
) -> bool:
    """Validate the X-Hub-Signature-256 header (constant-time compare)."""
    if not app_secret or not header:
        return False
    expected = "sha256=" + hmac.new(
        app_secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(header, expected)


def extract_media_id(text: str | None) -> str | None:
    """Extract the 16-character HD public ID from a WhatsApp message.

    Tolerant of case, punctuation and extra whitespace:
        "Send HD for ABC123XYZ789ABC"
        "SEND HD FOR abc123xyz789abc"
        "send hd for: ABC123XYZ789ABC"

    Falls back to accepting a message that contains exactly one 16-char
    alphanumeric token so simple ``<ID>`` messages also work without ever
    picking an arbitrary string out of a longer conversation.
    """
    if not text:
        return None
    phrase = _HD_ID_PHRASE.search(text)
    if phrase:
        return phrase.group(1).upper()
    tokens = _HD_ID_TOKEN.findall(text)
    if len(tokens) == 1:
        return tokens[0].upper()
    return None


def iter_events(payload: dict) -> list[dict]:
    """Normalize a Meta webhook payload into flat event dicts.

    Each event carries enough to persist a ``WhatsappWebhookEvent`` and to
    dispatch message/status processing in the worker.
    """
    events: list[dict] = []
    obj = payload.get("object")
    for entry in payload.get("entry", []) or []:
        entry_id = entry.get("id")
        changes = entry.get("changes", []) or []
        for change in changes:
            value = change.get("value", {}) or {}
            for msg in value.get("messages", []) or []:
                events.append(
                    {
                        "object": obj,
                        "entry_id": entry_id,
                        "event_type": "message",
                        "meta_message_id": msg.get("id"),
                        "message_type": msg.get("type", "unknown"),
                        "from_phone": msg.get("from"),
                        "text": _message_text(msg),
                        "timestamp": _safe_int(msg.get("timestamp")),
                        "meta": _metadata(msg, value),
                        "raw": msg,
                    }
                )
            for status in value.get("statuses", []) or []:
                events.append(
                    {
                        "object": obj,
                        "entry_id": entry_id,
                        "event_type": "status",
                        "meta_message_id": status.get("id"),
                        "delivery_status": status.get("status"),
                        "timestamp": _safe_int(status.get("timestamp")),
                        "meta": {"status": status},
                        "raw": status,
                    }
                )
    return events


def _message_text(msg: dict) -> str | None:
    if msg.get("type") == "text":
        body = (msg.get("text") or {}).get("body")
        return body if isinstance(body, str) else None
    return None


def _metadata(msg: dict, value: dict) -> dict:
    profile = (value.get("contacts") or [{}])[0].get("profile", {}) if value.get("contacts") else {}
    meta: dict = {
        "wa_id": value.get("contacts", [{}])[0].get("wa_id") if value.get("contacts") else None,
        "display_name": profile.get("name"),
    }
    if msg.get("type") in ("image", "video", "document", "audio", "sticker"):
        media = msg.get(msg["type"]) or {}
        meta["media"] = {
            key: media.get(key)
            for key in ("id", "mime_type", "sha256", "filename", "caption")
            if media.get(key) is not None
        }
    return {k: v for k, v in meta.items() if v is not None}


def _safe_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
