from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.upload import Upload
from app.repositories.base import BaseRepository

_UPLOAD_LOADS = (
    selectinload(Upload.media_files),
    selectinload(Upload.processed_media),
)


class UploadRepository(BaseRepository):
    model = Upload

    def _full_stmt(self, stmt):
        return stmt.options(*_UPLOAD_LOADS)

    def get_by_public_id(self, public_id: str, *, full: bool = False) -> Upload | None:
        stmt = select(Upload).where(Upload.public_id == public_id)
        if full:
            stmt = self._full_stmt(stmt)
        return self.db.scalar(stmt)

    def get_by_id(self, upload_id: uuid.UUID, *, full: bool = False) -> Upload | None:
        stmt = select(Upload).where(Upload.id == upload_id)
        if full:
            stmt = self._full_stmt(stmt)
        return self.db.scalar(stmt)
