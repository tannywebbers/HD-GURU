from __future__ import annotations

import datetime as dt
import uuid

from pydantic import EmailStr

from app.schemas.common import ORMModel


class UserOut(ORMModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: str
    is_active: bool
    email_verified: bool
    last_login_at: dt.datetime | None
    created_at: dt.datetime
    updated_at: dt.datetime
