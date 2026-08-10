from __future__ import annotations

import datetime as dt

from sqlalchemy import select

from app.models.auth_token import AuthToken
from app.repositories.base import BaseRepository


class AuthTokenRepository(BaseRepository[AuthToken]):
    model = AuthToken

    def get_active_by_hash(
        self, purpose: str, token_hash: str
    ) -> AuthToken | None:
        return self.db.scalar(
            select(AuthToken).where(
                AuthToken.purpose == purpose,
                AuthToken.token_hash == token_hash,
                AuthToken.used_at.is_(None),
                AuthToken.expires_at > dt.datetime.now(dt.timezone.utc),
            )
        )

    def invalidate_for_user(
        self, user_id, purpose: str, *, keep: AuthToken | None = None
    ) -> None:
        stmt = select(AuthToken).where(
            AuthToken.user_id == user_id,
            AuthToken.purpose == purpose,
            AuthToken.used_at.is_(None),
        )
        for token in self.db.scalars(stmt):
            if keep is not None and token.id == keep.id:
                continue
            token.used_at = dt.datetime.now(dt.timezone.utc)
