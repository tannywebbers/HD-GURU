from __future__ import annotations

from io import BytesIO

from PIL import Image

JPEG_MAGIC = b"\xff\xd8\xff\xe0"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
WEBM_MAGIC = b"\x1a\x45\xdf\xa3"


def jpeg_bytes(size: int = 1024) -> bytes:
    return JPEG_MAGIC + bytes(size - len(JPEG_MAGIC))


def png_bytes(size: int = 1024) -> bytes:
    return PNG_MAGIC + bytes(size - len(PNG_MAGIC))


def webm_bytes(size: int = 1024) -> bytes:
    return WEBM_MAGIC + bytes(size - len(WEBM_MAGIC))


def _encode_image(fmt: str, size: tuple[int, int] = (64, 64)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, "skyblue").save(buf, format=fmt)
    return buf.getvalue()


def real_jpeg_bytes() -> bytes:
    """A decodable JPEG the real Pillow pipeline can process."""
    return _encode_image("JPEG")


def real_png_bytes() -> bytes:
    return _encode_image("PNG")
