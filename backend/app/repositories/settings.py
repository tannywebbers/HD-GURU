from __future__ import annotations

from sqlalchemy import select

from app.models.setting import Setting
from app.repositories.base import BaseRepository


class SettingRepository(BaseRepository):
    model = Setting

    def all(self) -> list[Setting]:
        return list(
            self.db.scalars(
                select(Setting).order_by(Setting.group, Setting.key)
            )
        )

    def get_by_key(self, key: str) -> Setting | None:
        return self.db.scalar(select(Setting).where(Setting.key == key))
