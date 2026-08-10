from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.storage import get_storage
from app.models.media_file import MediaFile
from app.models.processed_media import ProcessedMedia
from app.services.whatsapp.errors import WhatsAppMediaError


def resolve_media_link(
    db: Session, processed: ProcessedMedia, media: MediaFile
) -> str | None:
    """Resolve a client-facing URL for the processed media.

    Prefers a storage URL when the backend is S3 (public or signed per
    MEDIA_URL_MODE). Falls back to the app's own ``/file`` route when the
    provider cannot produce a URL and ``APP_PUBLIC_BASE_URL`` is configured.

    Returns None when no publicly reachable URL can be built.
    """
    storage = get_storage()
    key = processed.processed_object_key or processed.storage_location
    if storage.provider == "s3":
        url = storage.media_url(
            key, expires_seconds=settings.MEDIA_SIGNED_URL_EXPIRES
        )
        if url:
            return url

    base = (settings.APP_PUBLIC_BASE_URL or "").strip().rstrip("/")
    if base:
        return f"{base}{settings.API_V1_PREFIX}/uploads/{media.public_id}/file"
    return None


def resolve_thumbnail_link(
    db: Session, processed: ProcessedMedia, media: MediaFile
) -> str | None:
    storage = get_storage()
    key = processed.thumbnail_object_key or processed.thumbnail_location
    if storage.provider == "s3" and key:
        url = storage.media_url(key, expires_seconds=settings.MEDIA_SIGNED_URL_EXPIRES)
        if url:
            return url
    base = (settings.APP_PUBLIC_BASE_URL or "").strip().rstrip("/")
    if base:
        return f"{base}{settings.API_V1_PREFIX}/uploads/{media.public_id}/thumbnail"
    return None


def send_type_for(mime_type: str) -> str:
    """Pick the WhatsApp message type for a processed media file."""
    mime = (mime_type or "").lower()
    if mime.startswith("image/"):
        return "image"
    if mime.startswith("video/"):
        return "video"
    return "document"


def media_send_payload(mime_type: str) -> dict:
    """Empty typed payload shell filled in by the caller with a link or id."""
    kind = send_type_for(mime_type)
    if kind == "image":
        return {"type": "image", "image": {}}
    if kind == "video":
        return {"type": "video", "video": {}}
    return {"type": "document", "document": {}}


def resolve_link_or_raise(db, processed, media) -> str:
    link = resolve_media_link(db, processed, media)
    if not link:
        raise WhatsAppMediaError(
            "The processed media has no publicly reachable URL. "
            "Configure APP_PUBLIC_BASE_URL (local storage) or an S3 public/signed "
            "URL (S3_PUBLIC_BASE_URL / MEDIA_URL_MODE)."
        )
    return link
