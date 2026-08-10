from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.responses import auth_responses, standard_responses
from app.core.database import get_db
from app.core.security import access_token_expires_in_seconds
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginHistoryPage,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    ResetPasswordRequest,
    TokenPair,
    VerifyEmailRequest,
)
from app.schemas.user import UserOut
from app.services import audit_service, auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

_TOKEN_PAIR_EXAMPLE = {
    "access_token": "<jwt>",
    "refresh_token": "<jwt>",
    "token_type": "bearer",
    "expires_in": 1800,
}


@router.post(
    "/login",
    response_model=TokenPair,
    summary="Authenticate a user",
    description=(
        "Validates email + password, records login history, updates the last "
        "login timestamp, counts failures and temporarily locks the account "
        "after repeated bad attempts. Returns an access/refresh token pair."
    ),
    responses={
        401: {
            "description": "Invalid credentials",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password."}
                    }
                }
            },
        },
        423: {
            "description": "Account temporarily locked",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": {"code": "ACCOUNT_LOCKED", "message": "Account temporarily locked. Try again later."}
                    }
                }
            },
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": {"code": "VALIDATION_ERROR", "message": "Request validation failed.", "details": []}
                    }
                }
            },
        },
    },
)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenPair:
    ip, user_agent = audit_service.client_meta(request)
    user = auth_service.login(
        db,
        payload.email,
        payload.password,
        ip_address=ip,
        user_agent=user_agent,
    )
    access, refresh = auth_service.create_token_pair(user)
    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=access_token_expires_in_seconds(),
    )


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Refresh tokens (rotation)",
    description=(
        "Consumes the refresh token (single-use) and returns a new access/"
        "refresh pair. Old tokens are revoked as part of rotation."
    ),
    responses=auth_responses(),
)
def refresh(
    payload: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenPair:
    ip, user_agent = audit_service.client_meta(request)
    access, refresh = auth_service.refresh_tokens(
        db, payload.refresh_token, ip_address=ip, user_agent=user_agent
    )
    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=access_token_expires_in_seconds(),
    )


@router.post(
    "/logout",
    status_code=204,
    summary="Revoke the current session",
    description=(
        "Revokes the provided refresh token and the current access token. "
        "A valid access token is required."
    ),
    responses=auth_responses(),
)
def logout(
    payload: LogoutRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> None:
    ip, user_agent = audit_service.client_meta(request)
    access_token = (
        authorization.removeprefix("Bearer ").strip()
        if authorization
        else None
    )
    auth_service.logout(
        db,
        payload.refresh_token,
        access_token,
        actor=current_user,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/logout-all",
    status_code=204,
    summary="Log out from every device",
    description=(
        "Bumps the user's token version so every previously issued access and "
        "refresh token is invalidated. Use after a suspected compromise."
    ),
    responses=auth_responses(),
)
def logout_all(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    ip, user_agent = audit_service.client_meta(request)
    auth_service.logout_all_devices(
        db, current_user, ip_address=ip, user_agent=user_agent
    )


@router.post(
    "/change-password",
    response_model=TokenPair,
    summary="Change the current password",
    description=(
        "Verifies the current password, stores the new one, and rotates the "
        "token version so all other sessions are signed out. Returns a fresh "
        "token pair for the current session."
    ),
    responses={
        **auth_responses(),
        400: {
            "description": "Wrong current password or weak new password",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": {"code": "WRONG_PASSWORD", "message": "Current password is incorrect."}
                    }
                }
            },
        },
    },
)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TokenPair:
    ip, user_agent = audit_service.client_meta(request)
    access, refresh = auth_service.change_password(
        db,
        current_user,
        payload.current_password,
        payload.new_password,
        ip_address=ip,
        user_agent=user_agent,
    )
    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=access_token_expires_in_seconds(),
    )


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    summary="Request a password reset",
    description=(
        "Issues a single-use password reset token and emails a reset link when "
        "the address is registered. The response is identical whether or not "
        "the address exists and never contains the token, so user enumeration "
        "is not possible."
    ),
    responses=auth_responses(),
)
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ForgotPasswordResponse:
    ip, user_agent = audit_service.client_meta(request)
    auth_service.request_password_reset(
        db, payload.email, ip_address=ip, user_agent=user_agent
    )
    message = (
        "If the address is registered, a password reset link has been sent."
    )
    return ForgotPasswordResponse(message=message)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset a password with a token",
    description=(
        "Consumes the single-use reset token and sets a new password. "
        "Clears the failed-login counter and lock, and signs out all devices."
    ),
    responses={
        **auth_responses(),
        400: {
            "description": "Invalid/expired token or weak password",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": {"code": "INVALID_RESET_TOKEN", "message": "The reset token is invalid or has expired."}
                    }
                }
            },
        },
    },
)
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> MessageResponse:
    ip, user_agent = audit_service.client_meta(request)
    auth_service.reset_password(
        db,
        payload.token,
        payload.new_password,
        ip_address=ip,
        user_agent=user_agent,
    )
    return MessageResponse(message="Password has been reset successfully.")


@router.post(
    "/email-verification",
    response_model=MessageResponse,
    summary="Request an email verification token",
    description=(
        "Issues a single-use email verification token for the current user. "
        "Only useful while EMAIL_VERIFICATION_REQUIRED is enabled."
    ),
    responses=auth_responses(),
)
def request_email_verification(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    ip, user_agent = audit_service.client_meta(request)
    token = auth_service.request_email_verification(
        db, current_user, ip_address=ip, user_agent=user_agent
    )
    return MessageResponse(
        message=f"Verification token issued. Use token '{token}' to verify."
    )


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    summary="Verify an email address",
    description=(
        "Consumes the single-use email verification token and marks the "
        "user's email as verified."
    ),
    responses={
        **auth_responses(),
        400: {
            "description": "Invalid/expired verification token",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": {"code": "INVALID_VERIFICATION_TOKEN", "message": "The verification token is invalid or has expired."}
                    }
                }
            },
        },
    },
)
def verify_email(
    payload: VerifyEmailRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> MessageResponse:
    ip, user_agent = audit_service.client_meta(request)
    auth_service.verify_email(
        db, payload.token, ip_address=ip, user_agent=user_agent
    )
    return MessageResponse(message="Email verified successfully.")


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get the current user",
    description="Returns the authenticated user's profile.",
    responses=standard_responses(),
)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get(
    "/login-history",
    response_model=LoginHistoryPage,
    summary="List recent login attempts",
    description=(
        "Returns the current user's recent login attempts (successful and "
        "failed), newest first, paginated."
    ),
    responses=standard_responses(),
)
def login_history(
    page: int = Query(1, ge=1, description="Page number, 1-based"),
    per_page: int = Query(
        20, ge=1, le=100, description="Items per page (1-100)"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LoginHistoryPage:
    result = auth_service.get_login_history(
        db, current_user, page=page, per_page=per_page
    )
    return LoginHistoryPage(
        items=result.items,
        total=result.total,
        page=result.page,
        per_page=result.per_page,
        pages=result.pages,
    )
