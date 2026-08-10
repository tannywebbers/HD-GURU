from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import log
from app.core.security import (
    consume_refresh_token,
    create_access_token,
    create_refresh_token,
    hash_password,
    revoke_access_token,
    revoke_all_user_tokens,
    revoke_refresh_token,
    verify_password,
)
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.login_history import LoginHistoryRepository
from app.repositories.users import UserRepository
from app.services import audit_service, email_service, token_service


def authenticate(db: Session, email: str, password: str) -> User | None:
    """Legacy helper kept for compatibility: password-only check."""
    user = UserRepository(db).get_by_email(email)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def login(
    db: Session,
    email: str,
    password: str,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> User:
    """Authenticate a user with lockout, failure counting and audit history.

    Raises AppError with ``ACCOUNT_LOCKED``, ``EMAIL_NOT_VERIFIED`` or
    ``INVALID_CREDENTIALS``.
    """
    repo = UserRepository(db)
    user = repo.get_by_email(email)
    login_repo = LoginHistoryRepository(db)

    if user is None or not user.is_active:
        login_repo.record(
            email=email,
            success=False,
            failure_reason="unknown_user",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.commit()
        raise AppError(401, "INVALID_CREDENTIALS", "Invalid email or password.")

    if user.is_locked:
        login_repo.record(
            email=email,
            success=False,
            user_id=user.id,
            failure_reason="account_locked",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.commit()
        raise AppError(
            423, "ACCOUNT_LOCKED", "Account temporarily locked. Try again later."
        )

    if not verify_password(password, user.password_hash):
        repo.record_failed_login(
            user,
            max_attempts=settings.FAILED_LOGIN_MAX_ATTEMPTS,
            lock_minutes=settings.ACCOUNT_LOCK_MINUTES,
        )
        login_repo.record(
            email=email,
            success=False,
            user_id=user.id,
            failure_reason="wrong_password",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        audit_service.log_action(
            db,
            action=audit_service.ACTION_LOGIN_FAILED,
            actor=user,
            details={"email": email},
            ip_address=ip_address,
            user_agent=user_agent,
            result="failure",
            commit=False,
        )
        db.commit()
        raise AppError(401, "INVALID_CREDENTIALS", "Invalid email or password.")

    if settings.EMAIL_VERIFICATION_REQUIRED and not user.email_verified:
        login_repo.record(
            email=email,
            success=False,
            user_id=user.id,
            failure_reason="email_not_verified",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.commit()
        raise AppError(
            403, "EMAIL_NOT_VERIFIED", "Please verify your email address first."
        )

    repo.record_successful_login(user)
    login_repo.record(
        email=email,
        success=True,
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    audit_service.log_action(
        db,
        action=audit_service.ACTION_LOGIN,
        actor=user,
        details={"email": email},
        ip_address=ip_address,
        user_agent=user_agent,
        commit=False,
    )
    db.commit()
    return user


def create_token_pair(user: User) -> tuple[str, str]:
    access = create_access_token(user)
    refresh = create_refresh_token(user)
    return access, refresh


def refresh_tokens(
    db: Session,
    refresh_token: str,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, str]:
    try:
        payload = consume_refresh_token(refresh_token)
    except Exception:
        raise AppError(
            401,
            "INVALID_REFRESH_TOKEN",
            "The refresh token is invalid or has expired.",
        ) from None

    user = db.get(User, payload.user_id)
    if user is None or not user.is_active:
        raise AppError(401, "INVALID_REFRESH_TOKEN", "The refresh token is invalid.")
    if payload.token_version != user.token_version:
        raise AppError(
            401, "TOKEN_STALE", "Tokens have been revoked. Please log in again."
        )

    access = create_access_token(user)
    refresh = create_refresh_token(user)
    audit_service.log_action(
        db,
        action=audit_service.ACTION_REFRESH,
        actor=user,
        ip_address=ip_address,
        user_agent=user_agent,
        commit=False,
    )
    db.commit()
    return access, refresh


def logout(
    db: Session,
    refresh_token: str,
    access_token: str | None = None,
    *,
    actor: User | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    revoke_refresh_token(refresh_token)
    if access_token:
        revoke_access_token(access_token)
    if actor is not None:
        audit_service.log_action(
            db,
            action=audit_service.ACTION_LOGOUT,
            actor=actor,
            ip_address=ip_address,
            user_agent=user_agent,
            commit=False,
        )
        db.commit()


def logout_all_devices(
    db: Session,
    user: User,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    revoke_all_user_tokens(user)
    audit_service.log_action(
        db,
        action=audit_service.ACTION_LOGOUT_ALL,
        actor=user,
        details={"token_version": user.token_version},
        ip_address=ip_address,
        user_agent=user_agent,
        commit=False,
    )
    db.commit()


def change_password(
    db: Session,
    user: User,
    current_password: str,
    new_password: str,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, str]:
    if not verify_password(current_password, user.password_hash):
        audit_service.log_action(
            db,
            action=audit_service.ACTION_CHANGE_PASSWORD,
            actor=user,
            ip_address=ip_address,
            user_agent=user_agent,
            result="failure",
            commit=False,
        )
        db.commit()
        raise AppError(400, "WRONG_PASSWORD", "Current password is incorrect.")

    if new_password == current_password:
        raise AppError(
            400, "PASSWORD_UNCHANGED", "New password must differ from current."
        )
    _validate_password_strength(new_password)

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    # Rotating every token forces other sessions to re-authenticate.
    revoke_all_user_tokens(user)
    audit_service.log_action(
        db,
        action=audit_service.ACTION_CHANGE_PASSWORD,
        actor=user,
        details={"token_version": user.token_version},
        ip_address=ip_address,
        user_agent=user_agent,
        commit=False,
    )
    db.commit()
    return create_access_token(user), create_refresh_token(user)


def request_password_reset(
    db: Session,
    email: str,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Issue a reset token and deliver it by email.

    The raw token is NEVER returned to the caller and is never included in an
    API response. The endpoint replies with the same message whether or not
    the address is registered, so user enumeration is not possible. Email
    delivery failures are logged without the token and do not change the
    response.
    """
    user = UserRepository(db).get_by_email(email)
    if user is None:
        return None
    raw = token_service.create_auth_token(
        db,
        user,
        purpose=token_service.PURPOSE_PASSWORD_RESET,
        ttl_hours=settings.PASSWORD_RESET_TOKEN_HOURS,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    audit_service.log_action(
        db,
        action=audit_service.ACTION_FORGOT_PASSWORD,
        actor=user,
        ip_address=ip_address,
        user_agent=user_agent,
        commit=False,
    )
    db.commit()
    try:
        email_service.send_password_reset_email(user.email, raw)
    except Exception as exc:
        # Never leak whether the address exists or expose the token.
        log.warning(
            "password_reset_email_failed",
            error_category="email_delivery",
            error=str(exc),
        )
    return None


def reset_password(
    db: Session,
    reset_token: str,
    new_password: str,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> User:
    _validate_password_strength(new_password)
    user = token_service.consume_auth_token(
        db, token_service.PURPOSE_PASSWORD_RESET, reset_token
    )
    if user is None:
        raise AppError(
            400,
            "INVALID_RESET_TOKEN",
            "The reset token is invalid or has expired.",
        )
    user.password_hash = hash_password(new_password)
    user.failed_login_count = 0
    user.locked_until = None
    revoke_all_user_tokens(user)
    audit_service.log_action(
        db,
        action=audit_service.ACTION_RESET_PASSWORD,
        actor=user,
        ip_address=ip_address,
        user_agent=user_agent,
        commit=False,
    )
    db.commit()
    return user


def request_email_verification(
    db: Session,
    user: User,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> str:
    if user.email_verified:
        raise AppError(400, "EMAIL_ALREADY_VERIFIED", "Email is already verified.")
    raw = token_service.create_auth_token(
        db,
        user,
        purpose=token_service.PURPOSE_EMAIL_VERIFY,
        ttl_hours=settings.EMAIL_VERIFICATION_TOKEN_HOURS,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    audit_service.log_action(
        db,
        action=audit_service.ACTION_EMAIL_VERIFY_REQUEST,
        actor=user,
        ip_address=ip_address,
        user_agent=user_agent,
        commit=False,
    )
    db.commit()
    return raw


def verify_email(
    db: Session,
    verification_token: str,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> User:
    user = token_service.consume_auth_token(
        db, token_service.PURPOSE_EMAIL_VERIFY, verification_token
    )
    if user is None:
        raise AppError(
            400,
            "INVALID_VERIFICATION_TOKEN",
            "The verification token is invalid or has expired.",
        )
    user.email_verified = True
    audit_service.log_action(
        db,
        action=audit_service.ACTION_EMAIL_VERIFY,
        actor=user,
        ip_address=ip_address,
        user_agent=user_agent,
        commit=False,
    )
    db.commit()
    return user


def get_login_history(
    db: Session,
    user: User,
    *,
    page: int = 1,
    per_page: int = 20,
):
    return LoginHistoryRepository(db).list_for_user(
        user.id, page=page, per_page=per_page
    )


def _validate_password_strength(password: str) -> None:
    min_length = settings.PASSWORD_MIN_LENGTH
    if len(password) < min_length:
        raise AppError(
            400,
            "WEAK_PASSWORD",
            f"Password must be at least {min_length} characters long.",
        )
    if password.isdigit() or password.isalpha():
        raise AppError(
            400,
            "WEAK_PASSWORD",
            "Password must contain a mix of letters and numbers.",
        )


def build_user_response(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value if isinstance(user.role, UserRole) else user.role,
        "is_active": user.is_active,
        "email_verified": user.email_verified,
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }
