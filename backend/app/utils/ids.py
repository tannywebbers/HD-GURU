from __future__ import annotations

import secrets
import string

ALPHABET = string.ascii_uppercase + string.ascii_lowercase + string.digits


def generate_public_id(length: int = 16) -> str:
    """Generate a cryptographically random alphanumeric public ID."""
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def generate_unique_public_id(
    session,
    model,
    length: int = 16,
    column: str = "public_id",
    max_attempts: int = 5,
) -> str:
    """Generate a unique public ID, retrying on the (astronomically rare)
    collision with an existing row so the DB uniqueness constraint is never
    the thing that surfaces."""
    from sqlalchemy import select

    for _ in range(max_attempts):
        candidate = generate_public_id(length)
        exists = session.scalar(
            select(model).where(getattr(model, column) == candidate)
        )
        if exists is None:
            return candidate
    raise RuntimeError("Could not allocate a unique public ID.")
