from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid
from app.models.enums import UserRole


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=generate_uuid
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        default=UserRole.USER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # --- authentication bookkeeping ---------------------------------------
    last_login_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    failed_login_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    locked_until: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    email_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    # Incremented on "logout all devices" to invalidate every issued JWT.
    token_version: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    uploads = relationship("Upload", back_populates="user")
    api_keys = relationship("ApiKey", back_populates="user")
    login_history = relationship(
        "LoginHistory",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    auth_tokens = relationship(
        "AuthToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @property
    def is_locked(self) -> bool:
        if self.locked_until is None:
            return False
        return self.locked_until > dt.datetime.now(dt.timezone.utc)
