from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base application error rendered as a structured JSON response."""

    def __init__(
        self,
        status_code: int = 400,
        error_code: str = "BAD_REQUEST",
        message: str = "Request failed.",
        details: Any = None,
    ) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details
        super().__init__(message)
