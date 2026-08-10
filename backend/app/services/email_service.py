from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from app.core.config import settings
from app.core.logging import log


class EmailDeliveryError(Exception):
    """Raised when a real SMTP delivery fails."""


def _from_address() -> str:
    name = settings.SMTP_FROM_NAME or settings.APP_NAME
    address = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME or "no-reply@localhost"
    return formataddr((name, address))


def reset_password_link(raw_token: str) -> str:
    """Build the reset URL the user opens. Never returned by the API."""
    base = settings.PASSWORD_RESET_URL.strip().rstrip("/")
    if not base:
        base = "/reset-password"
    separator = "&" if "?" in base else "?"
    return f"{base}{separator}token={raw_token}"


def _send_smtp(to_email: str, subject: str, text_body: str, html_body: str) -> None:
    """Send an email over SMTP using only the Python standard library."""
    message = MIMEMultipart("alternative")
    message["From"] = _from_address()
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(text_body, "plain", "utf-8"))
    if html_body:
        message.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as smtp:
            smtp.ehlo()
            if settings.SMTP_USE_TLS:
                smtp.starttls()
                smtp.ehlo()
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.sendmail(_from_address(), [to_email], message.as_string())
    except Exception as exc:
        # Do NOT include the recipient address or any token here.
        raise EmailDeliveryError(f"SMTP delivery failed: {exc}") from exc


def send_email(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> None:
    """Deliver an email via the configured backend.

    - ``EMAIL_BACKEND=smtp``: sends through SMTP (requires SMTP_* variables).
    - ``EMAIL_BACKEND=console``: development fallback that prints the message
      to the log so a developer can read the reset link. This backend is
      refused in a production environment so reset tokens never reach
      production logs.
    """
    backend = settings.EMAIL_BACKEND.strip().lower()

    if backend == "console":
        if settings.ENVIRONMENT.strip().lower() == "production":
            raise EmailDeliveryError(
                "EMAIL_BACKEND=console is not allowed in production; "
                "configure EMAIL_BACKEND=smtp with SMTP_* variables."
            )
        log.info(
            "email_console_out",
            to=to_email,
            subject=subject,
            body=text_body,
        )
        return

    if not settings.SMTP_HOST:
        raise EmailDeliveryError("SMTP_HOST is not configured.")
    _send_smtp(to_email, subject, text_body, html_body or "")


def send_password_reset_email(to_email: str, raw_token: str) -> None:
    """Send the password-reset message containing the single-use link."""
    link = reset_password_link(raw_token)
    app_name = settings.APP_NAME
    subject = f"Reset your {app_name} password"
    text_body = (
        f"Hello,\n\n"
        f"We received a request to reset your {app_name} password.\n\n"
        f"Open the link below to choose a new password (it expires in "
        f"{settings.PASSWORD_RESET_TOKEN_HOURS} hour"
        f"{'s' if settings.PASSWORD_RESET_TOKEN_HOURS != 1 else ''}):\n\n"
        f"{link}\n\n"
        f"If you did not request this, you can safely ignore this email.\n"
    )
    html_body = (
        "<p>Hello,</p>"
        f"<p>We received a request to reset your {app_name} password.</p>"
        "<p>Open the link below to choose a new password "
        f"(it expires in {settings.PASSWORD_RESET_TOKEN_HOURS} hour"
        f"{'s' if settings.PASSWORD_RESET_TOKEN_HOURS != 1 else ''}):</p>"
        f'<p><a href="{link}">{link}</a></p>'
        "<p>If you did not request this, you can safely ignore this email.</p>"
    )
    send_email(to_email, subject, text_body, html_body)
