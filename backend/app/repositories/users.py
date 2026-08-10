from __future__ import annotations

import datetime as dt

from sqlalchemy import select

from app.models.enums import UserRole
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(
            select(User).where(User.email == email.strip().lower())
        )

    def create_user(
        self,
        *,
        email: str,
        password_hash: str,
        full_name: str | None = None,
        role: UserRole = UserRole.USER,
        is_active: bool = True,
        email_verified: bool = False,
    ) -> User:
        return self.create(
            email=email.strip().lower(),
            password_hash=password_hash,
            full_name=full_name,
            role=role,
            is_active=is_active,
            email_verified=email_verified,
        )

    def record_successful_login(self, user: User) -> None:
        user.last_login_at = dt.datetime.now(dt.timezone.utc)
        user.failed_login_count = 0
        user.locked_until = None

    def record_failed_login(
        self, user: User, max_attempts: int, lock_minutes: int
    ) -> None:
        user.failed_login_count += 1
        if user.failed_login_count >= max_attempts:
            user.locked_until = dt.datetime.now(dt.timezone.utc) + dt.timedelta(
                minutes=lock_minutes
            )
