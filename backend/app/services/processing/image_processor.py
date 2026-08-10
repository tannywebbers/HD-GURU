from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from app.core.config import settings
from app.models.watermark import Watermark
from app.services.processing.common import (
    MediaProcessingError,
    ProcessingResult,
    prepare_watermark,
)

_JPEG_QUALITY_START = 95
_JPEG_QUALITY_FLOOR = 70
_THUMBNAIL_MAX = 320


def process_image(
    input_path: str,
    temp_dir: Path,
    watermark: Watermark | None,
) -> ProcessingResult:
    """Enhance an image and export a WhatsApp-friendly progressive JPEG.

    Applies EXIF orientation, strips all metadata, downscales to at most
    ``MAX_IMAGE_OUTPUT_DIMENSION``, applies a subtle sharpen/contrast, overlays
    the DB watermark, then encodes a progressive JPEG stepping quality down
    (and, if needed, dimensions) until the output is under the size target.
    """
    temp_dir = Path(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    img = _load_image(input_path)

    max_dim = settings.MAX_IMAGE_OUTPUT_DIMENSION
    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.LANCZOS)

    img = ImageEnhance.Contrast(img).enhance(1.05)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=80, threshold=3))

    wm_asset = prepare_watermark(
        watermark, img.width, img.height, temp_dir / "watermark.png"
    )
    if wm_asset is not None:
        with Image.open(wm_asset.png_path) as wm:
            wm = wm.convert("RGBA")
        img.paste(wm, (wm_asset.x, wm_asset.y), wm)

    jpeg_bytes = _encode_under_limit(img)

    output_path = temp_dir / "optimized.jpg"
    output_path.write_bytes(jpeg_bytes)

    thumbnail_path = temp_dir / "thumbnail.jpg"
    _write_thumbnail(img, thumbnail_path)

    return ProcessingResult(
        output_path=str(output_path),
        output_filename="optimized.jpg",
        thumbnail_path=str(thumbnail_path),
        mime_type="image/jpeg",
        extension="jpg",
        width=img.width,
        height=img.height,
        duration=None,
        file_size=len(jpeg_bytes),
        watermark_ref=wm_asset.ref if wm_asset is not None else None,
    )


def _load_image(path: str) -> Image.Image:
    try:
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im)
            return im.convert("RGB")
    except (OSError, ValueError, SyntaxError) as exc:
        raise MediaProcessingError("The image could not be decoded.") from exc


def _encode_jpeg(img: Image.Image, quality: int) -> bytes:
    buffer = io.BytesIO()
    img.save(
        buffer,
        "JPEG",
        quality=quality,
        optimize=True,
        progressive=True,
    )
    return buffer.getvalue()


def _encode_under_limit(img: Image.Image) -> bytes:
    quality = _JPEG_QUALITY_START
    data = _encode_jpeg(img, quality)
    while (
        len(data) > settings.max_image_output_size_bytes
        and quality > _JPEG_QUALITY_FLOOR
    ):
        quality -= 5
        data = _encode_jpeg(img, quality)

    current = img
    while (
        len(data) > settings.max_image_output_size_bytes
        and min(current.size) > 512
    ):
        w, h = current.size
        current = current.resize((int(w * 0.9), int(h * 0.9)), Image.LANCZOS)
        data = _encode_jpeg(current, quality)
    return data


def _write_thumbnail(img: Image.Image, out_path: Path) -> None:
    thumb = img.copy()
    thumb.thumbnail((_THUMBNAIL_MAX, _THUMBNAIL_MAX), Image.LANCZOS)
    thumb.save(out_path, "JPEG", quality=80, optimize=True)
