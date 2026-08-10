from __future__ import annotations

from app.services.whatsapp.client import WhatsAppGraphClient
from app.services.whatsapp.errors import WhatsAppValidationError


def _guard_number(to: str) -> None:
    digits = "".join(ch for ch in str(to) if ch.isdigit())
    if len(digits) < 10 or len(digits) > 15:
        raise WhatsAppValidationError("Invalid recipient phone number.")


def send_text_message(
    client: WhatsAppGraphClient,
    to: str,
    message: str,
    *,
    context: str | None = None,
) -> dict:
    """Send a plain text message. ``context`` optionally replies to a message."""
    _guard_number(to)
    return client.send_messages_payload(
        to,
        {
            "type": "text",
            "text": {"body": message, "preview_url": False},
        },
        context=context,
    )


def send_image_message(
    client: WhatsAppGraphClient,
    to: str,
    image_url: str,
    *,
    caption: str | None = None,
    context: str | None = None,
) -> dict:
    """Send an image by URL (no download into memory)."""
    _guard_number(to)
    image: dict = {"link": image_url}
    if caption:
        image["caption"] = caption
    return client.send_messages_payload(
        to, {"type": "image", "image": image}, context=context
    )


def send_video_message(
    client: WhatsAppGraphClient,
    to: str,
    video_url: str,
    *,
    caption: str | None = None,
    context: str | None = None,
) -> dict:
    """Send a video by URL."""
    _guard_number(to)
    video: dict = {"link": video_url}
    if caption:
        video["caption"] = caption
    return client.send_messages_payload(
        to, {"type": "video", "video": video}, context=context
    )


def send_document_message(
    client: WhatsAppGraphClient,
    to: str,
    document_url: str,
    *,
    filename: str | None = None,
    caption: str | None = None,
    context: str | None = None,
) -> dict:
    """Send a document by URL (used for non-image/video outputs)."""
    _guard_number(to)
    document: dict = {"link": document_url}
    if filename:
        document["filename"] = filename
    if caption:
        document["caption"] = caption
    return client.send_messages_payload(
        to, {"type": "document", "document": document}, context=context
    )
