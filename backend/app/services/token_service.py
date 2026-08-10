from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    generate_secure_token,
    hash_token,
    tokens_match,
)
from app.models.auth_token import AuthToken
from app.models.user import User
from app.repositories.auth_token import AuthTokenRepository

PURPOSE_PASSWORD_RESET = "password_reset"
PURPOSE_EMAIL_VERIFY = "email_verify"


def create_auth_token(
    db: Session,
    user: User,
    *,
    purpose: str,
    ttl_hours: int,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> str:
    """Create a single-use, hashed one-time token. Returns the raw token once."""
    repo = AuthTokenRepository(db)
    # Invalidate any previously issued, unused tokens for this purpose.
    repo.invalidate_for_user(user.id, purpose)
    raw = generate_secure_token()
    db.add(
        AuthToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=hash_token(raw),
            expires_at=dt.datetime.now(dt.timezone.utc)
            + dt.timedelta(hours=ttl_hours),
            ip_address=ip_address,
            user_agent=user_agent,
        )
    )
    db.commit()
    return raw


def consume_auth_token(
    db: Session, purpose: str, raw_token: str
) -> User | None:
    """Validate a one-time token and mark it used. Returns the owning user."""
    repo = AuthTokenRepository(db)
    row = repo.get_active_by_hash(purpose, hash_token(raw_token))
    if row is None or not tokens_match(raw_token, row.token_hash):
        return None
    row.used_at = dt.datetime.now(dt.timezone.utc)
    db.commit()
    return db.get(User, row.user_id)


def password_reset_ttl_hours() -> int:
    return settings.PASSWORD_RESET_TOKEN_HOURS


def email_verification_ttl_hours() -> int:
    return settings.EMAIL_VERIFICATION_TOKEN_HOURS
