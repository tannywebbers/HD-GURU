from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy.orm import Session

from app.models.base import Base
from app.utils.pagination import Page, paginate

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[Base] | None = None

    def __init__(self, db: Session) -> None:
        self.db = db

    def _model(self) -> type[ModelT]:
        if self.model is None:
            raise NotImplementedError("model is not set")
        return self.model

    def get(self, obj_id: Any) -> ModelT | None:
        return self.db.get(self._model(), obj_id)

    def create(self, **kwargs) -> ModelT:
        obj = self._model()(**kwargs)
        self.db.add(obj)
        return obj

    def add(self, obj: ModelT) -> ModelT:
        self.db.add(obj)
        return obj

    def delete(self, obj: ModelT) -> None:
        self.db.delete(obj)

    def commit(self) -> None:
        self.db.commit()

    def flush(self) -> None:
        self.db.flush()

    def refresh(self, obj: ModelT) -> None:
        self.db.refresh(obj)

    def paginate(self, stmt, *, page: int = 1, per_page: int = 20) -> Page[ModelT]:
        return paginate(self.db, stmt, page=page, per_page=per_page)
