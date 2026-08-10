from __future__ import annotations

import json
import socket
import time
from collections import deque
from urllib import error as urllib_error
from urllib import request as urllib_request

from app.core.config import settings
from app.core.logging import log
from app.services.whatsapp.config import WhatsAppConfig
from app.services.whatsapp.errors import (
    WhatsAppAuthError,
    WhatsAppConfigError,
    WhatsAppNotFoundError,
    WhatsAppRateLimitError,
    WhatsAppTemporaryError,
    WhatsAppValidationError,
)

_USER_AGENT = "HD-Guru/1.0"
# Graph error codes that map to specific, permanent outcomes.
_INVALID_TOKEN_CODES = {190}
_RATE_LIMIT_CODES = {4, 17, 613, 80007, 130429}
_MEDIA_PROCESSING_CODES = {131030, 131042, 132000}


class _OutboundRateLimiter:
    """Conservative per-process sliding-window send budget.

    Meta enforces its own per-tier limits (business-initiated vs
    user-initiated conversations). This is a local backstop so a bug can never
    produce an uncontrolled sending loop.
    """

    def __init__(self, max_per_minute: int) -> None:
        self._max = max_per_minute
        self._window: deque[float] = deque()

    def wait_or_raise(self) -> None:
        now = time.monotonic()
        while self._window and self._window[0] <= now - 60:
            self._window.popleft()
        if len(self._window) >= self._max:
            raise WhatsAppRateLimitError(
                "Outbound message rate limit reached. Please try again shortly."
            )
        self._window.append(now)


class WhatsAppGraphClient:
    """Minimal Graph API client for the WhatsApp Cloud API.

    Uses only the stdlib so there is no new runtime dependency. All calls go
    through ``_request`` which maps HTTP/transport failures onto the
    ``WhatsAppError`` hierarchy (transient errors are marked retryable).
    """

    def __init__(self, config: WhatsAppConfig) -> None:
        if not config.access_token or not config.phone_number_id:
            raise WhatsAppConfigError(
                "WhatsApp access token and phone number ID are required."
            )
        self._config = config
        self._limiter = _OutboundRateLimiter(
            settings.WHATSAPP_MAX_SENDS_PER_MINUTE
        )
        self._timeout = settings.WHATSAPP_SEND_TIMEOUT_SECONDS

    # --- auth helpers -------------------------------------------------------
    def _headers(self, *, multipart: bool = False) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._config.access_token}",
            "User-Agent": _USER_AGENT,
        }
        if not multipart:
            headers["Content-Type"] = "application/json"
        return headers

    def _build_url(self, endpoint: str, *, query: dict | None = None) -> str:
        base = self._config.messaging_endpoint() if endpoint == "messages" else self._config.media_endpoint()
        if query:
            from urllib.parse import urlencode

            base = f"{base}?{urlencode(query)}"
        return base

    # --- core request -------------------------------------------------------
    def _request(
        self,
        endpoint: str,
        payload: dict,
        *,
        method: str = "POST",
        query: dict | None = None,
    ) -> dict:
        url = self._build_url(endpoint, query=query)
        body = json.dumps(payload).encode("utf-8")
        req = urllib_request.Request(
            url, data=body, headers=self._headers(), method=method
        )
        try:
            with urllib_request.urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib_error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {}
            raise self._map_http_error(exc.code, data) from exc
        except (urllib_error.URLError, socket.timeout, TimeoutError) as exc:
            log.warning(
                "whatsapp graph transport error",
                endpoint=endpoint,
                error=str(exc),
            )
            raise WhatsAppTemporaryError(
                "Could not reach the WhatsApp API."
            ) from exc

    def _map_http_error(self, status: int, data: dict) -> WhatsAppError:
        err = data.get("error") or {}
        code = err.get("code")
        message = (err.get("message") or "WhatsApp API error.").strip()
        from app.services.whatsapp.errors import WhatsAppError

        if code in _INVALID_TOKEN_CODES or status == 401:
            return WhatsAppAuthError()
        if status == 429 or code in _RATE_LIMIT_CODES:
            return WhatsAppRateLimitError()
        if status in (500, 502, 503, 504):
            return WhatsAppTemporaryError()
        if status == 404:
            return WhatsAppNotFoundError()
        if status == 400 and code in _MEDIA_PROCESSING_CODES:
            return WhatsAppTemporaryError()
        return WhatsAppValidationError(
            f"WhatsApp rejected the request: {message}",
            code="WHATSAPP_VALIDATION_ERROR",
        )

    # --- messaging ----------------------------------------------------------
    def send_messages_payload(self, to: str, payload: dict, *, context: str | None = None) -> dict:
        self._limiter.wait_or_raise()
        body: dict = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            **payload,
        }
        if context:
            body["context"] = {"message_id": context}
        response = self._request("messages", body)
        message_ids = (response.get("messages") or []) if isinstance(response, dict) else []
        message_id = message_ids[0].get("id") if message_ids else None
        return {"response": response, "message_id": message_id}

    def test_credentials(self) -> dict:
        """Verify token + phone number id against the Graph API."""
        url = f"{self._config.graph_base()}/{self._config.phone_number_id}"
        req = urllib_request.Request(url, headers=self._headers(), method="GET")
        try:
            with urllib_request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return {
                "success": True,
                "message": "Connection verified.",
                "verified_name": data.get("verified_name"),
                "display_phone_number": data.get("display_phone_number"),
            }
        except urllib_error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {}
            mapped = self._map_http_error(exc.code, payload)
            reason = "The configured credentials were rejected by Meta."
            if isinstance(mapped, WhatsAppAuthError):
                reason = "The access token is missing, invalid or expired."
            elif isinstance(mapped, WhatsAppNotFoundError):
                reason = (
                    "The phone number ID was not found. Check WHATSAPP_PHONE_NUMBER_ID."
                )
            elif isinstance(mapped, WhatsAppValidationError):
                reason = "Meta rejected the request. Check your configuration."
            log.warning("whatsapp test_connection failed", reason=reason)
            return {"success": False, "message": reason}
        except (urllib_error.URLError, socket.timeout, TimeoutError):
            return {
                "success": False,
                "message": "Could not reach the WhatsApp API. Check the network and base URL.",
            }

    # --- media upload fallback ---------------------------------------------
    def upload_media(self, file_bytes: bytes, mime_type: str, *, filename: str) -> str:
        """Upload media bytes to Meta, returning the media ID.

        Only used when Meta cannot fetch media by URL (rare); prefer link-based
        sending so files are never pulled into memory on the worker.
        """
        boundary = "----hdguru" + str(int(time.time()))
        parts = []
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; "
            f'name="messaging_product"\r\n\r\nwhatsapp\r\n'
        )
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"type\"\r\n\r\n"
            f"{mime_type}\r\n"
        )
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; "
            f'name="file"; filename="{filename}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n"
        )
        body = "".join(parts).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode()
        url = self._config.media_endpoint()
        req = urllib_request.Request(
            url,
            data=body,
            headers={**self._headers(multipart=True), "Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        try:
            with urllib_request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data.get("id")
        except urllib_error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {}
            raise self._map_http_error(exc.code, payload) from exc
        except (urllib_error.URLError, socket.timeout, TimeoutError) as exc:
            raise WhatsAppTemporaryError("Could not upload media to WhatsApp.") from exc
