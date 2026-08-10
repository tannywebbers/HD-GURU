from __future__ import annotations

import datetime as dt
import uuid

from app.schemas.common import ORMModel


class MediaFileOut(ORMModel):
    id: uuid.UUID
    seq: int
    original_filename: str
    stored_filename: str
    mime_type: str
    extension: str
    file_size: int
    duration: float | None
    width: int | None
    height: int | None
    storage_location: str
    status: str
    created_at: dt.datetime


class ProcessedMediaOut(ORMModel):
    id: uuid.UUID
    original_filename: str
    processed_filename: str
    mime_type: str
    extension: str
    file_size: int
    width: int | None
    height: int | None
    duration: float | None
    storage_location: str
    status: str
    created_at: dt.datetime


class UploadOut(ORMModel):
    id: uuid.UUID
    public_id: str
    status: str
    original_filename: str
    optimized_filename: str | None
    mime_type: str
    extension: str
    file_size: int
    duration: float | None
    width: int | None
    height: int | None
    file_count: int
    download_count: int
    storage_location: str
    expires_at: dt.datetime
    created_at: dt.datetime
    updated_at: dt.datetime
    media_files: list[MediaFileOut]
    processed_media: list[ProcessedMediaOut]


class UploadSummary(ORMModel):
    """Limited view returned for anonymous lookups by public ID."""

    public_id: str
    status: str
    original_filename: str
    mime_type: str
    file_size: int
    file_count: int
    download_count: int
    expires_at: dt.datetime
    created_at: dt.datetime


class UploadCreateResponse(ORMModel):
    success: bool = True
    jobs: list[JobCreated]


class JobCreated(ORMModel):
    id: str
    status: str


class MediaStatusOut(ORMModel):
    """Per-file status payload returned by GET /uploads/{public_id}/status."""

    public_id: str
    status: str
    progress_stage: str
    media_type: str
    mime_type: str
    original_filename: str | None
    thumbnail_url: str | None
    download_url: str | None
    created_at: dt.datetime
    completed_at: dt.datetime | None
    error: str | None


class MediaResultOut(ORMModel):
    """Full per-file result returned by GET /uploads/{public_id}."""

    public_id: str
    status: str
    media_type: str
    original_filename: str
    mime_type: str
    file_size: int
    width: int | None
    height: int | None
    duration: float | None
    thumbnail_url: str | None
    download_url: str | None
    whatsapp_url: str | None
    created_at: dt.datetime
    completed_at: dt.datetime | None
    error: str | None
