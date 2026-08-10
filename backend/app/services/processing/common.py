from __future__ import annotations

import dataclasses
from pathlib import Path

from PIL import Image

from app.core.config import settings
from app.models.watermark import Watermark
from app.services.watermark_service import overlay_position, render_watermark


class MediaProcessingError(Exception):
    """Raised when a media file cannot be processed; message is user-safe."""


@dataclasses.dataclass
class ProcessingResult:
    output_path: str
    output_filename: str
    thumbnail_path: str | None
    mime_type: str
    extension: str
    width: int | None
    height: int | None
    duration: float | None
    file_size: int
    watermark_ref: dict | None = None


@dataclasses.dataclass
class WatermarkAsset:
    png_path: Path
    x: int
    y: int
    width: int
    height: int
    ref: dict


def prepare_watermark(
    watermark: Watermark | None,
    canvas_w: int,
    canvas_h: int,
    out_path: Path,
) -> WatermarkAsset | None:
    """Render the active DB watermark for a canvas of the given size.

    Opacity is baked into the PNG alpha; the asset is ready to composite at
    ``(x, y)`` by both the Pillow and FFmpeg pipelines. ``ref`` records the
    exact watermark config applied, stored on ProcessedMedia.watermark_ref.
    """
    if watermark is None or canvas_w <= 0 or canvas_h <= 0:
        return None

    render_watermark(watermark, canvas_w, canvas_h, out_path)
    with Image.open(out_path) as wm:
        wm_w, wm_h = wm.size

    if watermark.margin is not None and watermark.margin >= 0:
        margin = int(round(watermark.margin))
    else:
        margin = max(12, int(round(min(canvas_w, canvas_h) * 0.02)))
    x, y = overlay_position(
        watermark.position or "bottom-right",
        canvas_w,
        canvas_h,
        wm_w,
        wm_h,
        margin,
    )
    ref = {
        "name": watermark.name,
        "type": watermark.type,
        "position": watermark.position,
        "opacity": watermark.opacity,
        "size_percent": watermark.size_percent,
    }
    if margin >= 0:
        ref["margin"] = margin
    return WatermarkAsset(
        png_path=out_path,
        x=max(0, x),
        y=max(0, y),
        width=wm_w,
        height=wm_h,
        ref=ref,
    )


def target_video_dimensions(width: int, height: int) -> tuple[int, int]:
    """Compute output dimensions honoring the portrait/landscape/square caps.

    Portrait is capped at 1080x1920, landscape at 1920x1080, square at
    1080x1080. Aspect ratio is preserved and smaller originals are never
    upscaled. Returned dimensions are even (required by yuv420p).
    """
    if width <= 0 or height <= 0:
        raise MediaProcessingError("Video has invalid dimensions.")
    if width >= height:
        cap_w, cap_h = settings.MAX_VIDEO_WIDTH, settings.MAX_VIDEO_HEIGHT
    else:
        cap_w, cap_h = settings.MAX_VIDEO_HEIGHT, settings.MAX_VIDEO_WIDTH
    scale = min(1.0, cap_w / width, cap_h / height)
    out_w = int(width * scale) - (int(width * scale) % 2)
    out_h = int(height * scale) - (int(height * scale) % 2)
    return max(2, out_w), max(2, out_h)
