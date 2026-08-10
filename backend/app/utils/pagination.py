from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.sql import Select

from app.core.exceptions import AppError

T = TypeVar("T")


@dataclass
class Page(Generic[T]):
    items: list[T]
    total: int
    page: int
    per_page: int
    pages: int

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1


def validate_page_params(page: int, per_page: int) -> tuple[int, int]:
    if page < 1:
        raise AppError(400, "INVALID_PAGE", "Page must be at least 1.")
    if per_page < 1 or per_page > 100:
        raise AppError(
            400, "INVALID_PER_PAGE", "per_page must be between 1 and 100."
        )
    return page, per_page


def paginate(
    db,
    stmt: Select,
    *,
    page: int = 1,
    per_page: int = 20,
    model=None,
) -> Page:
    """Paginate a select statement. When ``model`` is given a count is issued
    with ``select(func.count()).select_from(stmt.subquery())`` which is the
    cheapest reliable path when the statement already has joins/distincts.
    """
    page, per_page = validate_page_params(page, per_page)
    total_stmt = (
        select(func.count()).select_from(stmt.subquery())
        if model is not None
        else select(func.count()).select_from(stmt.order_by(None).subquery())
    )
    total = int(db.scalar(total_stmt) or 0)
    rows = list(
        db.scalars(stmt.offset((page - 1) * per_page).limit(per_page)).all()
    )
    pages = max(1, (total + per_page - 1) // per_page)
    return Page(items=rows, total=total, page=page, per_page=per_page, pages=pages)
