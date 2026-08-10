from __future__ import annotations

import os
import shutil
import tempfile
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import boto3
from botocore.client import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectTimeoutError,
    EndpointConnectionError,
    NoCredentialsError,
    PartialCredentialsError,
    ReadTimeoutError,
)

from app.utils.files import sanitize_filename

_CHUNK_SIZE = 1024 * 1024
_TRANSIENT_RETRIES = 3
_TRANSIENT_BACKOFF = 0.5


class StorageError(Exception):
    """User-safe storage failure. ``code`` maps to an AppError code.

    Never carries a boto3 stack trace; only a short message plus enough
    context to log without leaking credentials.
    """

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


@dataclass
class StoredFile:
    seq: int
    original_filename: str
    stored_filename: str
    size: int
    path: str
    object_key: str | None = None


class BaseStorage(ABC):
    """Storage contract used by the upload service and the processing pipeline.

    Callers never know whether files live on a local disk or in an S3-compatible
    bucket; they only speak in public_id-relative locations / object keys.
    Business logic must never import boto3.
    """

    provider: str = "local"

    @abstractmethod
    def upload_dir(self, public_id: str) -> str: ...

    @abstractmethod
    def save_file(
        self,
        public_id: str,
        seq: int,
        original_filename: str,
        data: bytes,
        *,
        object_key: str | None = None,
    ) -> StoredFile: ...

    @abstractmethod
    def save_stream(
        self,
        public_id: str,
        seq: int,
        original_filename: str,
        stream: BinaryIO,
        *,
        max_bytes: int,
        initial: bytes = b"",
        object_key: str | None = None,
    ) -> StoredFile: ...

    @abstractmethod
    def save_bytes(
        self,
        public_id: str,
        subpath: str,
        filename: str,
        data: bytes,
        *,
        object_key: str | None = None,
    ) -> StoredFile:
        """Persist a processed artifact (optimized file, thumbnail, watermark PNG)
        under ``{public_id}/{subpath}/{filename}``."""

    @abstractmethod
    def copy_in(
        self,
        public_id: str,
        subpath: str,
        filename: str,
        source_path: str,
        *,
        max_bytes: int | None = None,
        object_key: str | None = None,
    ) -> StoredFile:
        """Stream-copy a local processed artifact into storage without loading
        it fully into memory."""

    @abstractmethod
    def download_to(self, key: str, dest_path: str) -> None:
        """Stream ``key`` to a local path (used by the worker to fetch originals)."""

    @abstractmethod
    def read_bytes(self, key: str) -> bytes: ...

    @abstractmethod
    def open_read(self, key: str) -> BinaryIO: ...

    @abstractmethod
    def delete_file(self, key: str) -> None: ...

    @abstractmethod
    def delete_object(self, key: str) -> None:
        """Idempotently remove a single object; missing objects are not an error."""

    @abstractmethod
    def delete_upload(self, public_id: str) -> None: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def public_url(self, key: str) -> str | None:
        """Direct public URL when the provider exposes one, else None."""

    @abstractmethod
    def signed_url(self, key: str, expires_seconds: int) -> str | None:
        """Short-lived signed URL when supported, else None."""

    @abstractmethod
    def media_url(self, key: str, *, expires_seconds: int) -> str | None:
        """Resolve ``key`` to a client-facing URL following MEDIA_URL_MODE.

        Returns None when the provider/configuration cannot produce a direct URL
        (e.g. local storage); callers then fall back to the app's own route.
        """


class LocalStorage(BaseStorage):
    """Local filesystem storage for uploaded + processed media."""

    provider = "local"

    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def upload_dir(self, public_id: str) -> str:
        directory = self.base_dir / public_id
        directory.mkdir(parents=True, exist_ok=True)
        return str(directory)

    def _as_stored(
        self,
        seq: int,
        original_filename: str,
        stored_filename: str,
        path: str,
    ) -> StoredFile:
        return StoredFile(
            seq=seq,
            original_filename=original_filename,
            stored_filename=stored_filename,
            size=Path(path).stat().st_size,
            path=path,
            object_key=path,
        )

    def save_file(
        self,
        public_id: str,
        seq: int,
        original_filename: str,
        data: bytes,
        *,
        object_key: str | None = None,
    ) -> StoredFile:
        directory = Path(self.upload_dir(public_id))
        safe_name = sanitize_filename(original_filename)
        stored_name = f"{seq}_{safe_name}" if safe_name else f"{seq}_file"
        path = directory / stored_name
        with open(path, "wb") as fh:
            fh.write(data)
        return self._as_stored(seq, original_filename, stored_name, str(path))

    def save_stream(
        self,
        public_id: str,
        seq: int,
        original_filename: str,
        stream: BinaryIO,
        *,
        max_bytes: int,
        initial: bytes = b"",
        object_key: str | None = None,
    ) -> StoredFile:
        """Stream ``stream`` to disk without buffering the whole file.

        ``initial`` is written first (the already-read signature head) so the
        stored size is correct even for files smaller than the head.

        Raises OverflowError if the stream exceeds ``max_bytes`` (the caller
        decides how to report it). The partial file is removed on overflow.
        """
        directory = Path(self.upload_dir(public_id))
        safe_name = sanitize_filename(original_filename)
        stored_name = f"{seq}_{safe_name}" if safe_name else f"{seq}_file"
        path = directory / stored_name
        size = len(initial)
        try:
            with open(path, "wb") as fh:
                if initial:
                    if size > max_bytes:
                        raise OverflowError("File exceeds maximum allowed size.")
                    fh.write(initial)
                while True:
                    chunk = stream.read(_CHUNK_SIZE)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > max_bytes:
                        raise OverflowError("File exceeds maximum allowed size.")
                    fh.write(chunk)
        except OverflowError:
            path.unlink(missing_ok=True)
            raise
        return self._as_stored(seq, original_filename, stored_name, str(path))

    def save_bytes(
        self,
        public_id: str,
        subpath: str,
        filename: str,
        data: bytes,
        *,
        object_key: str | None = None,
    ) -> StoredFile:
        directory = Path(self.upload_dir(public_id)) / subpath
        directory.mkdir(parents=True, exist_ok=True)
        safe_name = sanitize_filename(filename)
        stored_name = safe_name or "file"
        path = directory / stored_name
        with open(path, "wb") as fh:
            fh.write(data)
        return self._as_stored(0, filename, stored_name, str(path))

    def copy_in(
        self,
        public_id: str,
        subpath: str,
        filename: str,
        source_path: str,
        *,
        max_bytes: int | None = None,
        object_key: str | None = None,
    ) -> StoredFile:
        directory = Path(self.upload_dir(public_id)) / subpath
        directory.mkdir(parents=True, exist_ok=True)
        safe_name = sanitize_filename(filename)
        stored_name = safe_name or "file"
        path = directory / stored_name
        size = 0
        with open(source_path, "rb") as src, open(path, "wb") as dst:
            while True:
                chunk = src.read(_CHUNK_SIZE)
                if not chunk:
                    break
                size += len(chunk)
                if max_bytes is not None and size > max_bytes:
                    path.unlink(missing_ok=True)
                    raise OverflowError("Processed file exceeds the size budget.")
                dst.write(chunk)
        return self._as_stored(0, filename, stored_name, str(path))

    def download_to(self, key: str, dest_path: str) -> None:
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(key, dest)

    def read_bytes(self, key: str) -> bytes:
        with open(key, "rb") as fh:
            return fh.read()

    def open_read(self, key: str) -> BinaryIO:
        return open(key, "rb")

    def delete_file(self, key: str) -> None:
        Path(key).unlink(missing_ok=True)

    def delete_object(self, key: str) -> None:
        Path(key).unlink(missing_ok=True)

    def delete_upload(self, public_id: str) -> None:
        directory = self.base_dir / public_id
        if directory.exists():
            shutil.rmtree(directory, ignore_errors=True)

    def exists(self, key: str) -> bool:
        return Path(key).exists()

    def public_url(self, key: str) -> str | None:
        return None

    def signed_url(self, key: str, expires_seconds: int) -> str | None:
        return None

    def media_url(self, key: str, *, expires_seconds: int) -> str | None:
        return None

    def resolve(self, relative_path: str) -> Path:
        """Resolve a stored path, guarding against path traversal."""
        base = self.base_dir.resolve()
        candidate = (base / relative_path).resolve()
        if not str(candidate).startswith(str(base)):
            raise ValueError("Invalid storage path.")
        return candidate

    def check_writable(self) -> None:
        """Verify the storage root is present and writable (for health/readiness)."""
        probe = self.base_dir / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        if probe.read_text(encoding="utf-8") != "ok":
            raise OSError("Storage probe failed.")
        probe.unlink(missing_ok=True)


def _storage_error(action: str, exc: Exception) -> StorageError:
    """Convert a boto3/botocore exception into a user-safe StorageError."""
    if isinstance(exc, (NoCredentialsError, PartialCredentialsError)):
        return StorageError(
            500,
            "STORAGE_AUTH_ERROR",
            f"{action}: storage credentials are missing or incomplete.",
        )
    if isinstance(exc, ConnectTimeoutError):
        return StorageError(
            503,
            "STORAGE_TIMEOUT",
            f"{action}: the storage endpoint timed out.",
        )
    if isinstance(exc, (EndpointConnectionError, ReadTimeoutError)):
        return StorageError(
            503,
            "STORAGE_UNAVAILABLE",
            f"{action}: the storage service is unavailable.",
        )
    if isinstance(exc, ClientError):
        error = exc.response.get("Error", {}) or {}
        code = str(error.get("Code", ""))
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
        if code == "NoSuchBucket":
            return StorageError(
                500,
                "STORAGE_BUCKET_NOT_FOUND",
                f"{action}: the storage bucket does not exist.",
            )
        if code == "NoSuchKey" or status == 404:
            return StorageError(
                404,
                "STORAGE_OBJECT_NOT_FOUND",
                f"{action}: the requested object does not exist.",
            )
        if status == 403 or code in {
            "AccessDenied",
            "InvalidAccessKeyId",
            "SignatureDoesNotMatch",
            "InvalidToken",
        }:
            return StorageError(
                500,
                "STORAGE_PERMISSION_DENIED",
                f"{action}: storage access is denied. Check credentials and permissions.",
            )
        if status == 429 or code == "SlowDown":
            return StorageError(
                503,
                "STORAGE_THROTTLED",
                f"{action}: the storage service is throttling requests.",
            )
        if status >= 500:
            return StorageError(
                503,
                "STORAGE_UNAVAILABLE",
                f"{action}: the storage service is temporarily unavailable.",
            )
        return StorageError(
            500,
            "STORAGE_ERROR",
            f"{action}: the storage operation failed.",
        )
    return StorageError(
        500,
        "STORAGE_ERROR",
        f"{action}: the storage service is unavailable.",
    )


class S3CompatibleStorage(BaseStorage):
    """S3-compatible storage driver (Cloudflare R2 / AWS S3 / MinIO).

    All methods treat ``key`` values as object keys. Transient network and
    service errors are retried a bounded number of times; permanent errors
    (bad credentials, missing bucket, access denied) fail fast and are surfaced
    as ``StorageError`` with user-safe messages.
    """

    provider = "s3"

    def __init__(self) -> None:
        from app.core.config import settings

        self._settings = settings
        self.bucket = settings.S3_BUCKET_NAME
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION or "auto",
            config=Config(
                signature_version="s3v4",
                connect_timeout=10,
                read_timeout=60,
                retries={"max_attempts": _TRANSIENT_RETRIES, "mode": "standard"},
                s3={
                    "addressing_style": (
                        "path" if settings.S3_FORCE_PATH_STYLE else "auto"
                    )
                },
            ),
        )

    # --- internal helpers ----------------------------------------------------
    def _call(self, action: str, fn, *args, **kwargs):
        attempts = 0
        while True:
            try:
                return fn(*args, **kwargs)
            except (ConnectTimeoutError, ReadTimeoutError, EndpointConnectionError) as exc:
                attempts += 1
                if attempts >= _TRANSIENT_RETRIES:
                    raise _storage_error(action, exc) from exc
                time.sleep(_TRANSIENT_BACKOFF * attempts)
            except (NoCredentialsError, PartialCredentialsError) as exc:
                raise _storage_error(action, exc) from exc
            except ClientError as exc:
                raise _storage_error(action, exc) from exc
            except BotoCoreError as exc:
                raise _storage_error(action, exc) from exc

    def _fallback_key(
        self, public_id: str, subpath: str | None, filename: str
    ) -> str:
        safe = sanitize_filename(filename) or "file"
        if subpath:
            return f"{public_id}/{subpath}/{safe}"
        return f"{public_id}/{safe}"

    # --- lifecycle -----------------------------------------------------------
    def upload_dir(self, public_id: str) -> str:  # noqa: ARG002
        return f"s3://{self.bucket}"

    def save_file(
        self,
        public_id: str,
        seq: int,
        original_filename: str,
        data: bytes,
        *,
        object_key: str | None = None,
    ) -> StoredFile:
        key = object_key or self._fallback_key(public_id, None, original_filename)
        self._call(
            "upload",
            self._client.put_object,
            Bucket=self.bucket,
            Key=key,
            Body=data,
        )
        stored_name = sanitize_filename(original_filename) or "file"
        return StoredFile(
            seq=seq,
            original_filename=original_filename,
            stored_filename=stored_name,
            size=len(data),
            path=key,
            object_key=key,
        )

    def save_stream(
        self,
        public_id: str,
        seq: int,
        original_filename: str,
        stream: BinaryIO,
        *,
        max_bytes: int,
        initial: bytes = b"",
        object_key: str | None = None,
    ) -> StoredFile:
        key = object_key or self._fallback_key(public_id, None, original_filename)
        tmp = tempfile.NamedTemporaryFile(prefix="hdguru_stream_", delete=False)
        size = len(initial)
        try:
            if initial:
                if size > max_bytes:
                    raise OverflowError("File exceeds maximum allowed size.")
                tmp.write(initial)
            while True:
                chunk = stream.read(_CHUNK_SIZE)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise OverflowError("File exceeds maximum allowed size.")
                tmp.write(chunk)
            tmp.close()
            self._call(
                "upload",
                self._client.upload_file,
                tmp.name,
                self.bucket,
                key,
            )
        except OverflowError:
            tmp.close()
            Path(tmp.name).unlink(missing_ok=True)
            raise
        finally:
            Path(tmp.name).unlink(missing_ok=True)
        stored_name = sanitize_filename(original_filename) or "file"
        return StoredFile(
            seq=seq,
            original_filename=original_filename,
            stored_filename=stored_name,
            size=size,
            path=key,
            object_key=key,
        )

    def save_bytes(
        self,
        public_id: str,
        subpath: str,
        filename: str,
        data: bytes,
        *,
        object_key: str | None = None,
    ) -> StoredFile:
        key = object_key or self._fallback_key(public_id, subpath, filename)
        self._call(
            "upload",
            self._client.put_object,
            Bucket=self.bucket,
            Key=key,
            Body=data,
        )
        stored_name = sanitize_filename(filename) or "file"
        return StoredFile(
            seq=0,
            original_filename=filename,
            stored_filename=stored_name,
            size=len(data),
            path=key,
            object_key=key,
        )

    def copy_in(
        self,
        public_id: str,
        subpath: str,
        filename: str,
        source_path: str,
        *,
        max_bytes: int | None = None,
        object_key: str | None = None,
    ) -> StoredFile:
        size = os.path.getsize(source_path)
        if max_bytes is not None and size > max_bytes:
            raise OverflowError("Processed file exceeds the size budget.")
        key = object_key or self._fallback_key(public_id, subpath, filename)
        self._call(
            "upload",
            self._client.upload_file,
            source_path,
            self.bucket,
            key,
        )
        stored_name = sanitize_filename(filename) or "file"
        return StoredFile(
            seq=0,
            original_filename=filename,
            stored_filename=stored_name,
            size=size,
            path=key,
            object_key=key,
        )

    def download_to(self, key: str, dest_path: str) -> None:
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        self._call(
            "download",
            self._client.download_file,
            self.bucket,
            key,
            dest_path,
        )

    def read_bytes(self, key: str) -> bytes:
        response = self._call(
            "read",
            self._client.get_object,
            Bucket=self.bucket,
            Key=key,
        )
        return response["Body"].read()

    def open_read(self, key: str) -> BinaryIO:
        response = self._call(
            "read",
            self._client.get_object,
            Bucket=self.bucket,
            Key=key,
        )
        return response["Body"]

    def delete_file(self, key: str) -> None:
        self._call(
            "delete",
            self._client.delete_object,
            Bucket=self.bucket,
            Key=key,
        )

    def delete_object(self, key: str) -> None:
        self.delete_file(key)

    def delete_upload(self, public_id: str) -> None:
        """Remove any upload-scoped (legacy) objects. Per-object keys created
        in this phase are handled by delete_object calls from the service layer."""
        try:
            response = self._call(
                "list",
                self._client.list_objects_v2,
                Bucket=self.bucket,
                Prefix=f"{public_id}/",
            )
        except StorageError as exc:
            if exc.code == "STORAGE_BUCKET_NOT_FOUND":
                return
            raise
        keys = [obj["Key"] for obj in response.get("Contents", [])]
        while keys:
            batch = keys[:1000]
            self._call(
                "delete",
                self._client.delete_objects,
                Bucket=self.bucket,
                Delete={"Objects": [{"Key": k} for k in batch], "Quiet": True},
            )
            keys = keys[1000:]

    def exists(self, key: str) -> bool:
        try:
            self._call(
                "check",
                self._client.head_object,
                Bucket=self.bucket,
                Key=key,
            )
            return True
        except StorageError as exc:
            if exc.code == "STORAGE_OBJECT_NOT_FOUND":
                return False
            raise

    def public_url(self, key: str) -> str | None:
        base = (self._settings.S3_PUBLIC_BASE_URL or "").strip().rstrip("/")
        if not base:
            return None
        return f"{base}/{key}"

    def signed_url(self, key: str, expires_seconds: int) -> str | None:
        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_seconds,
            )
        except (ClientError, BotoCoreError) as exc:
            raise _storage_error("sign URL", exc) from exc

    def media_url(self, key: str, *, expires_seconds: int) -> str | None:
        mode = self._settings.MEDIA_URL_MODE
        if mode == "public":
            return self.public_url(key)
        if mode == "signed":
            return self.signed_url(key, expires_seconds)
        return None

    def check_writable(self) -> None:
        self._call("check", self._client.head_bucket, Bucket=self.bucket)


_storage: BaseStorage | None = None


def get_storage() -> BaseStorage:
    """Return the process-wide storage backend instance."""
    global _storage
    if _storage is None:
        from app.core.config import settings

        driver = settings.STORAGE_DRIVER
        if driver == "local":
            _storage = LocalStorage(settings.STORAGE_DIR)
        elif driver == "s3":
            _storage = S3CompatibleStorage()
        else:
            raise ValueError(f"Unsupported storage driver: {driver}")
    return _storage


def reset_storage() -> None:
    global _storage
    _storage = None
