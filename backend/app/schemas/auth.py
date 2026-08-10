from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.common import ORMModel


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., max_length=255)


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


class RequestEmailVerificationRequest(BaseModel):
    pass


class VerifyEmailRequest(BaseModel):
    token: str = Field(..., min_length=1)


class TokenPair(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class MessageResponse(BaseModel):
    message: str


class ForgotPasswordResponse(BaseModel):
    message: str


class LoginHistoryItem(ORMModel):
    id: uuid.UUID
    email: str
    success: bool
    failure_reason: str | None
    ip_address: str | None
    user_agent: str | None
    created_at: dt.datetime


class LoginHistoryPage(BaseModel):
    items: list[LoginHistoryItem]
    total: int
    page: int
    per_page: int
    pages: int
