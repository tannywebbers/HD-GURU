from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import log
from app.core.storage import StorageError, get_storage
from app.models.media_file import MediaFile
from app.models.processed_media import ProcessedMedia
from app.models.upload import Upload


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def _delete_objects(db: Session, upload: Upload) -> None:
    """Remove every stored object belonging to an upload (idempotent).

    Raises StorageError when a real storage failure occurs so the caller can
    keep the database rows for a later sweep. A missing object is not an error.
    """
    storage = get_storage()
    media_rows = list(
        db.scalars(select(MediaFile).where(MediaFile.upload_id == upload.id))
    )
    for media in media_rows:
        processed_rows = list(
            db.scalars(
                select(ProcessedMedia).where(ProcessedMedia.media_file_id == media.id)
            )
        )
        for processed in processed_rows:
            for key in (
                processed.processed_object_key or processed.storage_location,
                processed.thumbnail_object_key or processed.thumbnail_location,
            ):
                if key:
                    storage.delete_object(key)
        original = media.original_object_key or media.storage_location
        if original:
            storage.delete_object(original)
    storage.delete_upload(upload.public_id)


def run_expiry_cleanup(db: Session, *, batch_size: int = 50) -> dict:
    """Delete expired uploads and their stored objects.

    Works for both local and cloud storage: objects are deleted via the
    storage driver (never the filesystem directly) and rows are removed only
    after their objects are gone. Uploads whose objects cannot be deleted are
    kept for a later sweep.
    """
    now = _now()
    expired = list(
        db.scalars(
            select(Upload)
            .where(Upload.expires_at.is_not(None), Upload.expires_at < now)
            .order_by(Upload.expires_at.asc())
            .limit(batch_size)
        )
    )
    if not expired:
        return {"uploads_deleted": 0, "media_deleted": 0, "errors": 0}

    uploads_deleted = 0
    media_deleted = 0
    errors = 0
    for upload in expired:
        try:
            _delete_objects(db, upload)
            media_deleted += upload.file_count or 0
            db.delete(upload)
            db.commit()
            uploads_deleted += 1
        except StorageError as exc:
            db.rollback()
            errors += 1
            log.warning(
                "expiry cleanup kept upload (storage failure)",
                public_id=upload.public_id,
                code=exc.code,
            )
        except Exception:
            db.rollback()
            errors += 1
            log.exception(
                "expiry cleanup failed for upload",
                public_id=upload.public_id,
            )

    return {
        "uploads_deleted": uploads_deleted,
        "media_deleted": media_deleted,
        "errors": errors,
    }
