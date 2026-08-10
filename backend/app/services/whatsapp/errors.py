from __future__ import annotations


class WhatsAppError(Exception):
    """Base error for the WhatsApp integration.

    ``code`` is a stable machine-readable string. ``retryable`` marks errors
    that should be retried by the background worker (transient failures);
    permanent errors fail fast. Messages never contain credentials.
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        http_status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.http_status = http_status


class WhatsAppConfigError(WhatsAppError):
    """Missing or invalid WhatsApp configuration."""

    def __init__(self, message: str) -> None:
        super().__init__("WHATSAPP_CONFIG_ERROR", message, http_status=500)


class WhatsAppAuthError(WhatsAppError):
    """Invalid, missing or expired access token."""

    def __init__(self, message: str = "WhatsApp credentials are invalid.") -> None:
        super().__init__("WHATSAPP_AUTH_ERROR", message, http_status=401)


class WhatsAppNotFoundError(WhatsAppError):
    """The requested resource does not exist on Meta's side."""

    def __init__(self, message: str = "WhatsApp resource not found.") -> None:
        super().__init__("WHATSAPP_NOT_FOUND", message, http_status=404)


class WhatsAppValidationError(WhatsAppError):
    """Meta rejected the payload (bad phone number id, invalid media URL, ...)."""

    def __init__(self, message: str, code: str = "WHATSAPP_VALIDATION_ERROR") -> None:
        super().__init__(code, message, http_status=400)


class WhatsAppRateLimitError(WhatsAppError):
    """Rate limited by Meta or by the local outbound budget."""

    def __init__(self, message: str = "WhatsApp rate limit reached.") -> None:
        super().__init__(
            "WHATSAPP_RATE_LIMITED", message, retryable=True, http_status=429
        )


class WhatsAppTemporaryError(WhatsAppError):
    """Transient failure (network timeout, 5xx). Safe to retry."""

    def __init__(self, message: str = "WhatsApp is temporarily unavailable.") -> None:
        super().__init__(
            "WHATSAPP_TEMPORARY_ERROR", message, retryable=True, http_status=503
        )


class WhatsAppMediaError(WhatsAppError):
    """Media could not be resolved, fetched or uploaded."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(
            "WHATSAPP_MEDIA_ERROR",
            message,
            retryable=retryable,
            http_status=502,
        )


class WhatsAppWebhookError(WhatsAppError):
    """Webhook verification or signature validation failed."""

    def __init__(self, message: str, http_status: int = 403) -> None:
        super().__init__("WHATSAPP_WEBHOOK_ERROR", message, http_status=http_status)
