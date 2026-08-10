from __future__ import annotations

import datetime as dt
import shutil
import tempfile
from pathlib import Path

from celery import Task
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import log
from app.core.storage import get_storage
from app.models.enums import JobStatus, MediaStatus, UploadStatus
from app.models.job import Job
from app.models.media_file import MediaFile
from app.models.processed_media import ProcessedMedia
from app.models.upload import Upload
from app.services import system_log_service
from app.services.processing import (
    MediaProcessingError,
    process_image,
    process_video,
)
from app.services.watermark_service import get_active_watermark
from app.utils.object_keys import media_object_key
from app.workers.celery_app import celery_app

_MAX_ERROR_LENGTH = 500


def _safe_error_message(exc: Exception, temp_root: str | None = None) -> str:
    """Return a user-safe error string that never leaks filesystem paths.

    The worker runs with temporary directories and a local storage dir that
    embed the public id; those paths must not reach users or the admin panel.
    """
    text = str(exc) or exc.__class__.__name__
    if temp_root:
        text = text.replace(temp_root, "<temp>")
    if settings.STORAGE_DIR:
        text = text.replace(str(settings.STORAGE_DIR), "<storage>")
    return text[:_MAX_ERROR_LENGTH]


@celery_app.task(
    bind=True,
    name="uploads.process",
    max_retries=3,
    default_retry_delay=30,
    retry_backoff=True,
    retry_backoff_max=300,
)
def process_upload(self: Task, job_id: str, public_id: str) -> dict:
    """Process every media file of an upload through the enhancement pipeline.

    Each file moves through queued -> analyzing -> enhancing -> watermarking ->
    compressing -> storing -> completed (or failed). Stages are committed to the
    database as they happen so the status endpoint reports real progress.
    """
    temp_root = tempfile.mkdtemp(prefix=f"hdguru_{public_id}_")
    try:
        with SessionLocal() as db:
            upload = db.scalar(
                select(Upload).where(Upload.public_id == public_id)
            )
            job = db.get(Job, _uuid(job_id))

            if upload is None or job is None:
                log.error(
                    "processing job references missing records",
                    job_id=job_id,
                    public_id=public_id,
                )
                return {"public_id": public_id, "status": "noop"}

            job.status = JobStatus.RUNNING
            job.started_at = dt.datetime.now(dt.timezone.utc)
            job.worker_id = self.request.hostname if self.request else None
            upload.status = UploadStatus.PROCESSING
            db.commit()

            files = list(
                db.scalars(
                    select(MediaFile)
                    .where(MediaFile.upload_id == upload.id)
                    .order_by(MediaFile.seq)
                )
            )

            if upload.expires_at is not None and upload.expires_at < dt.datetime.now(
                dt.timezone.utc
            ).replace(tzinfo=None):
                for file in files:
                    file.status = MediaStatus.EXPIRED
                upload.status = UploadStatus.FAILED
                job.status = JobStatus.SUCCEEDED
                job.finished_at = dt.datetime.now(dt.timezone.utc)
                job.result = {"public_id": public_id, "status": "expired"}
                db.commit()
                return {"public_id": public_id, "status": "expired"}

            watermark = get_active_watermark(db)

            completed = 0
            failed = 0
            for file in files:
                if _process_file(db, file, watermark, temp_root, upload.public_id):
                    completed += 1
                else:
                    failed += 1

            upload.status = (
                UploadStatus.COMPLETED if completed else UploadStatus.FAILED
            )
            if completed:
                first_processed = db.scalar(
                    select(ProcessedMedia)
                    .where(ProcessedMedia.upload_id == upload.id)
                    .order_by(ProcessedMedia.created_at.asc())
                    .limit(1)
                )
                if first_processed is not None:
                    upload.optimized_filename = first_processed.processed_filename

            job.status = (
                JobStatus.SUCCEEDED if completed else JobStatus.FAILED
            )
            job.finished_at = dt.datetime.now(dt.timezone.utc)
            job.result = {
                "public_id": public_id,
                "files_total": len(files),
                "files_completed": completed,
                "files_failed": failed,
                "engine": "media-pipeline",
            }
            db.commit()

            log.info(
                "upload processed",
                public_id=public_id,
                completed=completed,
                failed=failed,
            )
            return {
                "public_id": public_id,
                "status": "completed" if completed else "failed",
                "files_completed": completed,
                "files_failed": failed,
            }
    except Exception as exc:
        log.exception(
            "upload processing failed",
            public_id=public_id,
            error=str(exc),
        )
        with SessionLocal() as db:
            upload = db.scalar(
                select(Upload).where(Upload.public_id == public_id)
            )
            if upload is not None:
                upload.status = UploadStatus.FAILED
                for file in db.scalars(
                    select(MediaFile).where(MediaFile.upload_id == upload.id)
                ):
                    if file.status == MediaStatus.QUEUED:
                        file.status = MediaStatus.FAILED
                        file.error = _safe_error_message(exc, temp_root)
                job = db.get(Job, _uuid(job_id))
                if job is not None:
                    job.status = JobStatus.FAILED
                    job.traceback = _safe_error_message(exc, temp_root)
                    job.finished_at = dt.datetime.now(dt.timezone.utc)
                db.commit()
        system_log_service.record_error(
            message="upload processing failed",
            logger_name="worker",
            context={"public_id": public_id, "job_id": job_id, "error": str(exc)},
        )
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


@celery_app.task(name="uploads.cleanup_expired")
def cleanup_expired() -> dict:
    """Delete expired uploads and their stored objects (local or cloud)."""
    from app.services.cleanup_service import run_expiry_cleanup

    with SessionLocal() as db:
        result = run_expiry_cleanup(db)
    log.info("expiry cleanup run", **result)
    return result


@celery_app.task(
    bind=True,
    name="whatsapp.process_event",
    max_retries=5,
    default_retry_delay=10,
    retry_backoff=True,
    retry_backoff_max=300,
)
def process_whatsapp_event(self: Task, event_id: str) -> dict:
    """Process one persisted WhatsApp webhook event in the background.

    The webhook endpoint acknowledges immediately; delivery happens here.
    Only transient WhatsApp errors (rate limits, 5xx, timeouts) are retried;
    permanent failures are recorded on the event and fail fast.
    """
    from app.services.whatsapp import service as whatsapp_service
    from app.services.whatsapp.errors import WhatsAppError

    event_uuid = _uuid(event_id)
    if event_uuid is None:
        log.warning("whatsapp event has invalid id", event_id=event_id)
        return {"status": "invalid_event_id"}

    try:
        with SessionLocal() as db:
            return whatsapp_service.process_event(db, event_uuid)
    except WhatsAppError as exc:
        log.warning(
            "whatsapp event transient failure",
            event_id=event_id,
            code=exc.code,
            retries=self.request.retries,
        )
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        with SessionLocal() as db:
            whatsapp_service.mark_event_failed(db, event_uuid, exc.message)
        system_log_service.record_error(
            message="whatsapp webhook event failed after retries",
            logger_name="worker",
            context={"event_id": event_id, "code": exc.code},
        )
        return {"status": "failed", "code": exc.code}
    except Exception as exc:
        log.exception(
            "whatsapp event unexpected failure",
            event_id=event_id,
            error=str(exc),
        )
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        raise


@celery_app.task(name="analytics.retention_run")
def run_analytics_retention() -> dict:
    """Purge raw analytics/ad event rows older than the retention window.

    Scheduled by beat (see ``celery_app.py``) so ANALYTICS_RETENTION_DAYS is
    actually enforced in production; the admin endpoint is the manual trigger.
    """
    from app.services import analytics_service
    from app.services.ads.service import analytics_retention_days

    with SessionLocal() as db:
        result = analytics_service.run_retention(
            db, days=analytics_retention_days(db)
        )
    log.info("analytics retention run", **result)
    return result


def _process_file(
    db, file: MediaFile, watermark, temp_root: str, upload_public_id: str
) -> bool:
    """Run one media file through the pipeline. Returns True on success."""
    storage = get_storage()
    file_dir = Path(temp_root) / file.public_id
    file_dir.mkdir(parents=True, exist_ok=True)

    try:
        _set_status(db, file, MediaStatus.ANALYZING)
        original_key = file.original_object_key or file.storage_location
        source_path = file.storage_location
        if storage.provider == "s3":
            source_path = str(Path(temp_root) / f"{file.public_id}_original.bin")
            storage.download_to(original_key, source_path)
        if file.mime_type.startswith("image/"):
            result = process_image(source_path, file_dir, watermark)
        elif file.mime_type.startswith("video/"):
            result = process_video(source_path, file_dir, watermark)
        else:
            raise MediaProcessingError(
                f"Unsupported media type: {file.mime_type}."
            )

        _set_status(db, file, MediaStatus.ENHANCING)
        _set_status(db, file, MediaStatus.WATERMARKING)
        _set_status(db, file, MediaStatus.COMPRESSING)
        _set_status(db, file, MediaStatus.STORING)

        output_budget = (
            settings.max_video_output_size_bytes
            if result.mime_type.startswith("video/")
            else settings.max_image_output_size_bytes
        )
        when = dt.datetime.now(dt.timezone.utc)
        processed_key = media_object_key(
            "processed", file.public_id, result.extension, when
        )
        # Processed artifacts live under the upload's directory so a single
        # delete_upload call removes originals + results together.
        stored_output = storage.copy_in(
            upload_public_id,
            f"{file.public_id}/optimized",
            result.output_filename,
            result.output_path,
            max_bytes=output_budget + (1024 * 1024),
            object_key=processed_key,
        )
        stored_thumb = None
        if result.thumbnail_path:
            thumbnail_key = media_object_key(
                "thumbnails", file.public_id, "jpg", when
            )
            stored_thumb = storage.copy_in(
                upload_public_id,
                f"{file.public_id}/thumbnails",
                "thumbnail.jpg",
                result.thumbnail_path,
                object_key=thumbnail_key,
            )

        now = dt.datetime.now(dt.timezone.utc)
        db.add(
            ProcessedMedia(
                upload_id=file.upload_id,
                media_file_id=file.id,
                original_filename=file.original_filename,
                processed_filename=result.output_filename,
                mime_type=result.mime_type,
                extension=result.extension,
                file_size=result.file_size,
                width=result.width,
                height=result.height,
                duration=result.duration,
                storage_location=stored_output.path,
                thumbnail_location=stored_thumb.path if stored_thumb else None,
                storage_provider=storage.provider,
                processed_object_key=stored_output.object_key,
                thumbnail_object_key=(
                    stored_thumb.object_key if stored_thumb else None
                ),
                watermark_ref=result.watermark_ref,
                status=MediaStatus.COMPLETED,
                completed_at=now,
            )
        )
        file.status = MediaStatus.COMPLETED
        file.error = None
        file.width = result.width
        file.height = result.height
        file.duration = result.duration
        db.commit()
        return True
    except (MediaProcessingError, OSError, OverflowError) as exc:
        db.rollback()
        file.status = MediaStatus.FAILED
        file.error = _safe_error_message(exc, temp_root)
        db.commit()
        log.warning(
            "media file processing failed",
            public_id=file.public_id,
            error=str(exc),
        )
        return False


def _set_status(db, file: MediaFile, status: MediaStatus) -> None:
    file.status = status
    db.commit()


def _uuid(value: str):
    import uuid

    try:
        return uuid.UUID(value)
    except ValueError:
        return None
