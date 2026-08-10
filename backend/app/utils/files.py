from __future__ import annotations

import os
import re

from app.core.exceptions import AppError

# Magic-byte signatures for the formats we accept. `head` bytes -> detected MIME.
_MAGIC_RULES: list[tuple[str, bytes, str]] = [
    ("jpeg", b"\xff\xd8\xff", "image/jpeg"),
    ("png", b"\x89PNG\r\n\x1a\n", "image/png"),
    ("gif", b"GIF87a", "image/gif"),
    ("gif", b"GIF89a", "image/gif"),
    ("bmp", b"BM", "image/bmp"),
    ("tiff_le", b"II*\x00", "image/tiff"),
    ("tiff_be", b"MM\x00*", "image/tiff"),
    ("webm", b"\x1a\x45\xdf\xa3", "video/webm"),
]


def _box_type(head: bytes) -> str | None:
    """ISO-BMFF (mp4/mov/m4v) and HEIF box type at offset 4."""
    if len(head) >= 12 and head[4:8] == b"ftyp":
        return head[8:12].decode("latin-1")
    return None


def _detect_mime(head: bytes) -> str | None:
    if not head:
        return None

    for _, magic, mime in _MAGIC_RULES:
        if head.startswith(magic):
            return mime

    if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        return "image/webp"
    if head.startswith(b"RIFF") and head[8:12] == b"AVI ":
        return "video/x-msvideo"

    box = _box_type(head)
    if box is not None:
        if box in {"heic", "heix", "hevc", "hevx", "mif1", "msf1"}:
            return "image/heic"
        if box in {"qt  "}:
            return "video/quicktime"
        if box == "M4V ":
            return "video/x-m4v"
        if box in {"mp4", "mp41", "mp42", "isom", "iso2", "avc1", "dash"}:
            return "video/mp4"
    return None


# Declared MIME -> family used for cross-checking against detected bytes.
_MIME_TO_FAMILY: dict[str, str] = {
    "image/jpeg": "jpeg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
    "image/bmp": "bmp",
    "image/tiff": "tiff",
    "image/heic": "heic",
    "image/heif": "heic",
    "video/mp4": "mp4",
    "video/x-m4v": "m4v",
    "video/quicktime": "mov",
    "video/webm": "webm",
    "video/x-msvideo": "avi",
    "video/x-matroska": "mkv",
}

_DETECTED_TO_FAMILY: dict[str, str] = {
    "image/jpeg": "jpeg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
    "image/bmp": "bmp",
    "image/tiff": "tiff",
    "image/heic": "heic",
    "video/mp4": "mp4",
    "video/x-m4v": "m4v",
    "video/quicktime": "mov",
    "video/webm": "webm",
    "video/x-msvideo": "avi",
    "video/x-matroska": "mkv",
}

# Family -> extensions the actual filename may carry.
_FAMILY_TO_EXTENSIONS: dict[str, set[str]] = {
    "jpeg": {"jpg", "jpeg"},
    "png": {"png"},
    "gif": {"gif"},
    "webp": {"webp"},
    "bmp": {"bmp"},
    "tiff": {"tiff", "tif"},
    "heic": {"heic", "heif"},
    "mp4": {"mp4"},
    "m4v": {"m4v"},
    "mov": {"mov"},
    "webm": {"webm"},
    "avi": {"avi"},
    "mkv": {"mkv"},
}


def extension_from_mime(mime: str) -> str:
    return {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/gif": "gif",
        "image/webp": "webp",
        "image/bmp": "bmp",
        "image/tiff": "tiff",
        "image/heic": "heic",
        "image/heif": "heif",
        "video/mp4": "mp4",
        "video/x-m4v": "m4v",
        "video/quicktime": "mov",
        "video/webm": "webm",
        "video/x-msvideo": "avi",
        "video/x-matroska": "mkv",
    }.get(mime, "bin")


def sanitize_filename(filename: str) -> str:
    base = os.path.basename(filename or "").strip()
    cleaned = re.sub(r"[^\w.\- ]", "_", base).strip().rstrip(".")
    return cleaned[:200] or "file"


def get_extension(filename: str | None) -> str:
    if not filename:
        return ""
    base = os.path.basename(filename)
    _, ext = os.path.splitext(base)
    return ext.lstrip(".").lower()


def validate_head(
    *,
    filename: str | None,
    declared_mime: str | None,
    head: bytes,
    allowed_mime_types: list[str],
    allowed_extensions: list[str],
) -> tuple[str, str]:
    """Validate the leading bytes + declared MIME + filename extension.

    Returns (effective_mime, extension). Raises AppError on any mismatch.
    This is the streaming equivalent of ``validate_file`` and must run before
    the rest of the file body is streamed to disk.
    """
    declared = (declared_mime or "").lower().strip()
    detected = _detect_mime(head)

    if detected is not None:
        family = _DETECTED_TO_FAMILY.get(detected)
        declared_family = _MIME_TO_FAMILY.get(declared)
        if declared_family and family and declared_family != family:
            raise AppError(
                400,
                "FILE_TYPE_MISMATCH",
                f"File '{filename or '?'}' content does not match its declared type.",
            )
        effective_mime = detected
    else:
        effective_mime = declared

    if effective_mime not in allowed_mime_types:
        raise AppError(
            400,
            "UNSUPPORTED_FILE_TYPE",
            f"Unsupported file type: {effective_mime or 'unknown'}.",
        )

    ext = get_extension(filename)
    allowed = set(allowed_extensions) if allowed_extensions else set()
    if ext and allowed and ext not in allowed:
        raise AppError(
            400,
            "UNSUPPORTED_EXTENSION",
            f"Extension '.{ext}' is not allowed.",
        )

    family = _MIME_TO_FAMILY.get(effective_mime)
    valid_extensions = _FAMILY_TO_EXTENSIONS.get(family or "", set())
    if ext and allowed and valid_extensions and ext not in valid_extensions:
        raise AppError(
            400,
            "EXTENSION_MISMATCH",
            f"Extension '.{ext}' does not match the file content.",
        )

    return effective_mime, extension_from_mime(effective_mime)


def validate_file(
    filename: str | None,
    declared_mime: str | None,
    data: bytes,
    allowed_mime_types: list[str],
    *,
    max_file_size: int,
    max_upload_size: int,
    current_total: int,
    allowed_extensions: list[str] | None = None,
) -> tuple[str, str]:
    """Validate a whole file and return (detected_mime, extension).

    Raises AppError for unsupported types, mismatched content, or oversize.
    """
    size = len(data)
    if size == 0:
        raise AppError(400, "EMPTY_FILE", "Empty files are not allowed.")

    if size > max_file_size:
        raise AppError(
            400,
            "FILE_TOO_LARGE",
            f"File '{filename or '?'}' exceeds the maximum allowed size.",
        )

    if current_total + size > max_upload_size:
        raise AppError(
            400,
            "UPLOAD_TOO_LARGE",
            "Total upload size exceeds the maximum allowed size.",
        )

    return validate_head(
        filename=filename,
        declared_mime=declared_mime,
        head=data[:1024],
        allowed_mime_types=allowed_mime_types,
        allowed_extensions=allowed_extensions or [],
    )