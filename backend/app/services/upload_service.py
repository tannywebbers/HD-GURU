from __future__ import annotations

import datetime as dt
import os
import uuid

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import log
from app.core.storage import BaseStorage, get_storage
from app.models.enums import JobStatus, MediaStatus, UploadStatus
from app.models.job import Job
from app.models.media_file import MediaFile
from app.models.processed_media import ProcessedMedia
from app.models.upload import Upload
from app.models.user import User
from app.repositories.uploads import UploadRepository
from app.services import audit_service, system_log_service
from app.services.settings_service import get_setting_int
from app.utils.files import validate_head
from app.utils.ids import generate_unique_public_id
from app.utils.object_keys import media_object_key
_HEAD_SIZE = 1024


def create_upload(
    db: Session,
    files: list[UploadFile],
    *,
    user: User | None,
    ip_address: str | None,
    user_agent: str | None,
) -> Upload:
    total = len(files)
    if total < 1:
        raise AppError(400, "NO_FILES", "At least one file is required.")
    if total > settings.MAX_UPLOAD_FILES:
        raise AppError(
            400,
            "TOO_MANY_FILES",
            f"At most {settings.MAX_UPLOAD_FILES} files are allowed per upload.",
        )

    public_id = generate_unique_public_id(db, Upload)
    storage = get_storage()
    when = dt.datetime.now(dt.timezone.utc)
    prepared: list[tuple[int, str, str, str, int, str, str | None]] = []
    saved: list = []
    total_size = 0

    try:
        for seq, file in enumerate(files, start=1):
            media_public_id = generate_unique_public_id(db, MediaFile)
            head = _read_head(file)
            mime, ext = validate_head(
                filename=file.filename,
                declared_mime=file.content_type,
                head=head,
                allowed_mime_types=settings.allowed_mime_types,
                allowed_extensions=settings.allowed_extensions,
            )
            remaining = settings.max_upload_size_bytes - total_size
            if remaining <= 0:
                raise AppError(
                    400,
                    "UPLOAD_TOO_LARGE",
                    "Total upload size exceeds the maximum allowed size.",
                )
            original_key = media_object_key("original", media_public_id, ext, when)
            try:
                stored = storage.save_stream(
                    public_id,
                    seq,
                    file.filename or "file",
                    file.file,
                    max_bytes=min(settings.max_file_size_bytes, remaining),
                    initial=head,
                    object_key=original_key,
                )
            except OverflowError:
                raise AppError(
                    400,
                    "FILE_TOO_LARGE",
                    f"File '{file.filename or '?'}' exceeds the maximum allowed size.",
                ) from None
            if stored.size == 0:
                raise AppError(400, "EMPTY_FILE", "Empty files are not allowed.")
            total_size += stored.size
            prepared.append(
                (
                    seq,
                    file.filename or "file",
                    mime,
                    ext,
                    stored.size,
                    media_public_id,
                    stored.object_key,
                )
            )
            saved.append(stored)
    except AppError:
        storage.delete_upload(public_id)
        raise
    except Exception:
        storage.delete_upload(public_id)
        log.exception("failed to persist uploaded files", public_id=public_id)
        system_log_service.record_error(
            message="storage write failed",
            logger_name="storage",
            context={"public_id": public_id},
        )
        raise AppError(
            500, "STORAGE_ERROR", "Failed to store uploaded files."
        ) from None

    first_name = prepared[0][1]
    first_mime = prepared[0][2]
    first_ext = prepared[0][3]
    ttl_hours = get_setting_int(
        db, "upload.ttl_hours", settings.DEFAULT_UPLOAD_TTL_HOURS
    )
    if ttl_hours <= 0:
        ttl_hours = settings.DEFAULT_UPLOAD_TTL_HOURS
    expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=ttl_hours)

    upload = Upload(
        public_id=public_id,
        user_id=user.id if user else None,
        original_filename=first_name,
        mime_type=first_mime,
        extension=first_ext,
        file_size=total_size,
        storage_location=storage.upload_dir(public_id),
        status=UploadStatus.QUEUED,
        file_count=total,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires_at,
    )
    db.add(upload)
    db.flush()

    for (seq, original_name, mime, ext, size, media_public_id, object_key), stored in zip(
        prepared, saved
    ):
        db.add(
            MediaFile(
                upload_id=upload.id,
                public_id=media_public_id,
                seq=seq,
                original_filename=original_name,
                stored_filename=stored.stored_filename,
                mime_type=mime,
                extension=ext,
                file_size=size,
                storage_location=stored.path,
                storage_provider=storage.provider,
                original_object_key=object_key,
                status=MediaStatus.QUEUED,
            )
        )

    job = Job(
        job_type="uploads.process",
        upload_id=upload.id,
        status=JobStatus.QUEUED,
        args={"public_id": public_id},
    )
    db.add(job)
    audit_service.log_action(
        db,
        action=audit_service.ACTION_UPLOAD_CREATE,
        actor=user,
        resource_type="upload",
        resource_id=str(upload.id),
        details={"public_id": public_id, "file_count": total},
        ip_address=ip_address,
        user_agent=user_agent,
        commit=False,
    )
    db.commit()
    db.refresh(upload)

    _enqueue(db, job, public_id)
    return upload


def _read_head(file: UploadFile) -> bytes:
    try:
        return file.file.read(_HEAD_SIZE) if hasattr(file, "file") else b""
    except Exception:
        return b""


def _enqueue(db: Session, job: Job, public_id: str) -> None:
    from app.workers.tasks import process_upload

    task_id: str | None = None
    try:
        result = process_upload.apply_async(
            args=[str(job.id), public_id], kwargs={}
        )
        task_id = getattr(result, "id", None)
    except Exception:
        log.exception(
            "failed to enqueue processing job; will remain queued",
            public_id=public_id,
        )
        system_log_service.record_warning(
            message="failed to enqueue processing job",
            logger_name="worker",
            context={"public_id": public_id},
        )

    if task_id:
        job.celery_task_id = task_id
        db.add(job)
        db.commit()


def get_upload(db: Session, upload_ref: str, *, full: bool = False) -> Upload | None:
    repo = UploadRepository(db)
    try:
        uid = uuid.UUID(upload_ref)
        return repo.get_by_id(uid, full=full)
    except ValueError:
        return repo.get_by_public_id(upload_ref, full=full)


def delete_upload(
    db: Session,
    upload: Upload,
    *,
    actor: User | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    storage = get_storage()
    media_rows = list(
        db.scalars(
            select(MediaFile).where(MediaFile.upload_id == upload.id)
        )
    )
    for media in media_rows:
        processed_rows = list(
            db.scalars(
                select(ProcessedMedia).where(
                    ProcessedMedia.media_file_id == media.id
                )
            )
        )
        for processed in processed_rows:
            _delete_object_keys(
                storage,
                [
                    processed.processed_object_key or processed.storage_location,
                    processed.thumbnail_object_key or processed.thumbnail_location,
                ],
            )
        _delete_object_keys(storage, [media.original_object_key or media.storage_location])
    storage.delete_upload(upload.public_id)
    audit_service.log_action(
        db,
        action=audit_service.ACTION_UPLOAD_DELETE,
        actor=actor,
        resource_type="upload",
        resource_id=str(upload.id),
        details={"public_id": upload.public_id},
        ip_address=ip_address,
        user_agent=user_agent,
        commit=False,
    )
    db.delete(upload)
    db.commit()


def upload_storage_path(upload: Upload) -> str:
    return os.path.join(settings.STORAGE_DIR, upload.public_id)


def delete_media_file(
    db: Session,
    media: MediaFile,
    *,
    actor: User | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Delete a single media file, its processed artifacts and its records."""
    storage = get_storage()
    processed_rows = list(
        db.scalars(
            select(ProcessedMedia).where(
                ProcessedMedia.media_file_id == media.id
            )
        )
    )
    for processed in processed_rows:
        _delete_object_keys(
            storage,
            [
                processed.processed_object_key or processed.storage_location,
                processed.thumbnail_object_key or processed.thumbnail_location,
            ],
        )
        db.delete(processed)
    _delete_object_keys(storage, [media.original_object_key or media.storage_location])
    audit_service.log_action(
        db,
        action=audit_service.ACTION_UPLOAD_DELETE,
        actor=actor,
        resource_type="media_file",
        resource_id=str(media.id),
        details={"public_id": media.public_id},
        ip_address=ip_address,
        user_agent=user_agent,
        commit=False,
    )
    db.delete(media)
    db.commit()


def _delete_object_keys(storage: BaseStorage, keys: list[str | None]) -> None:
    """Delete objects idempotently; a missing object is treated as success."""
    for key in keys:
        if key:
            storage.delete_object(key)
