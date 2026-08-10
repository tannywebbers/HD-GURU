from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_user_optional
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.storage import get_storage
from app.models.enums import MediaStatus, UserRole
from app.models.media_file import MediaFile
from app.models.processed_media import ProcessedMedia
from app.models.upload import Upload
from app.models.user import User
from app.schemas.upload import (
    JobCreated,
    MediaResultOut,
    MediaStatusOut,
    UploadCreateResponse,
    UploadOut,
    UploadSummary,
)
from app.services import upload_service
from app.services.whatsapp import config as whatsapp_config

router = APIRouter(prefix="/uploads", tags=["Uploads"])


@router.post(
    "",
    response_model=UploadCreateResponse,
    status_code=201,
    summary="Upload 1 to 5 media files",
    description=(
        "Validates count, MIME type, magic-byte signature, extension and size "
        "before streaming files to storage. Rejects corrupted, oversized or "
        "mismatched uploads before anything is persisted. Each accepted file "
        "is returned as a job with its own 16-character public ID."
    ),
)
def create_upload(
    request: Request,
    files: list[UploadFile] = File(...),
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> UploadCreateResponse:
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    upload = upload_service.create_upload(
        db,
        files,
        user=current_user,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    jobs = [
        JobCreated(id=media.public_id, status=media.status.value)
        for media in upload.media_files
    ]
    return UploadCreateResponse(success=True, jobs=jobs)


@router.get(
    "/{upload_id}/status",
    response_model=MediaStatusOut,
    summary="Get the processing status of one media file",
)
def get_upload_status(
    upload_id: str,
    db: Session = Depends(get_db),
) -> MediaStatusOut:
    media = _resolve_media(db, upload_id)
    if media is None:
        raise AppError(404, "MEDIA_NOT_FOUND", "Media file not found.")

    upload = db.get(Upload, media.upload_id)
    processed = _latest_processed(db, media.id)

    if upload is not None and _is_expired(upload):
        effective_status = MediaStatus.EXPIRED.value
    else:
        effective_status = media.status.value

    return MediaStatusOut(
        public_id=media.public_id,
        status=effective_status,
        progress_stage=effective_status,
        media_type=_media_type(media.mime_type),
        mime_type=media.mime_type,
        original_filename=media.original_filename,
        thumbnail_url=_thumbnail_url(media.public_id, processed),
        download_url=_download_url(media.public_id, processed, effective_status),
        created_at=media.created_at,
        completed_at=processed.completed_at if processed else None,
        error=media.error,
    )


@router.get(
    "/{upload_id}",
    summary="Get an upload batch or a single media file by public ID",
)
def get_upload(
    upload_id: str,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    upload = upload_service.get_upload(db, upload_id, full=True)
    if upload is not None:
        if _is_expired(upload):
            raise AppError(410, "EXPIRED", "This upload has expired.")
        if current_user is None:
            return UploadSummary.model_validate(upload)
        if _can_access(current_user, upload):
            return UploadOut.model_validate(upload)
        raise AppError(403, "FORBIDDEN", "You cannot access this upload.")

    media = _resolve_media(db, upload_id)
    if media is not None:
        upload = db.get(Upload, media.upload_id)
        if upload is not None and _is_expired(upload):
            raise AppError(410, "EXPIRED", "This media file has expired.")
        processed = _latest_processed(db, media.id)
        return MediaResultOut(
            public_id=media.public_id,
            status=media.status.value,
            media_type=_media_type(media.mime_type),
            original_filename=media.original_filename,
            mime_type=media.mime_type,
            file_size=processed.file_size if processed else media.file_size,
            width=processed.width if processed else media.width,
            height=processed.height if processed else media.height,
            duration=processed.duration if processed else media.duration,
            thumbnail_url=_thumbnail_url(media.public_id, processed),
            download_url=_download_url(media.public_id, processed, media.status.value),
            whatsapp_url=whatsapp_config.build_whatsapp_link(media.public_id, db),
            created_at=media.created_at,
            completed_at=processed.completed_at if processed else None,
            error=media.error,
        )

    raise AppError(404, "UPLOAD_NOT_FOUND", "Upload not found.")


@router.get(
    "/{upload_id}/file",
    response_model=None,
    summary="Download the processed media file",
)
def download_media(
    upload_id: str,
    db: Session = Depends(get_db),
):
    media = _resolve_media(db, upload_id)
    if media is None:
        raise AppError(404, "MEDIA_NOT_FOUND", "Media file not found.")

    upload = db.get(Upload, media.upload_id)
    if upload is not None and _is_expired(upload):
        raise AppError(410, "EXPIRED", "This media file has expired.")

    processed = _latest_processed(db, media.id)
    if processed is None or processed.status != MediaStatus.COMPLETED:
        raise AppError(409, "NOT_READY", "The processed file is not ready yet.")

    storage = get_storage()
    key = processed.processed_object_key or processed.storage_location
    if storage.provider == "s3":
        url = storage.media_url(
            key, expires_seconds=settings.MEDIA_SIGNED_URL_EXPIRES
        )
        if url is None:
            raise AppError(
                500, "STORAGE_URL_UNAVAILABLE", "Cannot generate a media URL."
            )
        processed.download_count += 1
        db.commit()
        _track_media_delivery(media.public_id)
        return RedirectResponse(url)

    if not storage.exists(key):
        raise AppError(404, "FILE_MISSING", "The processed file is missing.")

    processed.download_count += 1
    db.commit()
    _track_media_delivery(media.public_id)

    filename = processed.processed_filename or f"{media.public_id}.{processed.extension}"
    return FileResponse(
        key,
        media_type=processed.mime_type,
        filename=filename,
    )


@router.get(
    "/{upload_id}/thumbnail",
    response_model=None,
    summary="Get the thumbnail of a processed media file",
)
def get_thumbnail(
    upload_id: str,
    db: Session = Depends(get_db),
):
    media = _resolve_media(db, upload_id)
    if media is None:
        raise AppError(404, "MEDIA_NOT_FOUND", "Media file not found.")

    upload = db.get(Upload, media.upload_id)
    if upload is not None and _is_expired(upload):
        raise AppError(410, "EXPIRED", "This media file has expired.")

    processed = _latest_processed(db, media.id)
    if processed is None or not (processed.thumbnail_location or processed.thumbnail_object_key):
        raise AppError(404, "THUMBNAIL_MISSING", "No thumbnail is available.")

    storage = get_storage()
    key = processed.thumbnail_object_key or processed.thumbnail_location
    if storage.provider == "s3":
        url = storage.media_url(
            key, expires_seconds=settings.MEDIA_SIGNED_URL_EXPIRES
        )
        if url is None:
            raise AppError(
                500, "STORAGE_URL_UNAVAILABLE", "Cannot generate a thumbnail URL."
            )
        return RedirectResponse(url)

    if not storage.exists(key):
        raise AppError(404, "THUMBNAIL_MISSING", "No thumbnail is available.")

    return FileResponse(key, media_type="image/jpeg")


@router.delete(
    "/{upload_id}",
    status_code=204,
    summary="Delete an upload batch or a single media file",
    description=(
        "Anonymous public deletion by 16-char public ID, or owner/admin deletion."
    ),
)
def delete_upload(
    upload_id: str,
    request: Request,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> Response:
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    upload = upload_service.get_upload(db, upload_id, full=False)
    if upload is not None:
        if current_user is not None and not _can_access(current_user, upload):
            raise AppError(403, "FORBIDDEN", "You cannot delete this upload.")
        upload_service.delete_upload(
            db,
            upload,
            actor=current_user,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return Response(status_code=204)

    media = _resolve_media(db, upload_id)
    if media is not None:
        upload_service.delete_media_file(
            db,
            media,
            actor=current_user,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return Response(status_code=204)

    raise AppError(404, "UPLOAD_NOT_FOUND", "Upload not found.")


def _resolve_media(db: Session, public_id: str) -> MediaFile | None:
    return db.scalar(select(MediaFile).where(MediaFile.public_id == public_id))


def _latest_processed(db: Session, media_id) -> ProcessedMedia | None:
    return db.scalar(
        select(ProcessedMedia)
        .where(ProcessedMedia.media_file_id == media_id)
        .order_by(ProcessedMedia.created_at.desc())
        .limit(1)
    )


def _is_expired(upload: Upload) -> bool:
    if upload.expires_at is None:
        return False
    # Normalize to naive UTC so the comparison is safe on both SQLite (naive)
    # and Postgres (tz-aware) — comparing aware vs naive raises TypeError.
    now_utc = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    return upload.expires_at.replace(tzinfo=None) < now_utc


def _media_type(mime: str) -> str:
    return "image" if mime.startswith("image/") else "video"


def _thumbnail_url(public_id: str, processed: ProcessedMedia | None) -> str | None:
    if processed is None or not (processed.thumbnail_location or processed.thumbnail_object_key):
        return None
    key = processed.thumbnail_object_key or processed.thumbnail_location
    storage = get_storage()
    if storage.provider == "s3":
        url = storage.media_url(
            key, expires_seconds=settings.MEDIA_SIGNED_URL_EXPIRES
        )
        if url is not None:
            return url
    return f"{settings.API_V1_PREFIX}/uploads/{public_id}/thumbnail"


def _download_url(
    public_id: str, processed: ProcessedMedia | None, status: str
) -> str | None:
    if processed is None or status != MediaStatus.COMPLETED.value:
        return None
    key = processed.processed_object_key or processed.storage_location
    storage = get_storage()
    if storage.provider == "s3":
        url = storage.media_url(
            key, expires_seconds=settings.MEDIA_SIGNED_URL_EXPIRES
        )
        if url is not None:
            return url
    return f"{settings.API_V1_PREFIX}/uploads/{public_id}/file"


def _can_access(user: User, upload: Upload) -> bool:
    if user.role == UserRole.ADMIN:
        return True
    return upload.user_id is not None and upload.user_id == user.id


def _track_media_delivery(public_id: str) -> None:
    """Best-effort analytics hook; never affects the download response."""
    try:
        from app.core.database import SessionLocal
        from app.services.analytics_service import track_event

        with SessionLocal() as db:
            track_event(
                db,
                event="media_delivered",
                session_id=None,
                page=f"/uploads/{public_id}",
            )
    except Exception:
        pass
