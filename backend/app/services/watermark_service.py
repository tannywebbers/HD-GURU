from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.watermark import Watermark

# All 9 supported anchor positions.
POSITIONS = (
    "top-left",
    "top-center",
    "top-right",
    "middle-left",
    "middle-center",
    "middle-right",
    "bottom-left",
    "bottom-center",
    "bottom-right",
)

_DEFAULT_POSITION = "bottom-right"
_DEFAULT_OPACITY = 0.35
_DEFAULT_SIZE_PERCENT = 8.0

_FONT_CANDIDATES = (
    "arial.ttf",
    "DejaVuSans.ttf",
    "DejaVuSans-Bold.ttf",
    "Verdana.ttf",
    "segoeui.ttf",
    "Tahoma.ttf",
    "LiberationSans-Regular.ttf",
)


class WatermarkUnavailable(Exception):
    """Raised when no usable watermark config can be produced."""


def get_active_watermark(db: Session) -> Watermark | None:
    """Return the active watermark configuration, or None when disabled.

    The watermark is never hardcoded into the pipeline: it always comes from
    the ``watermarks`` table. If none is configured yet, a sensible default
    text watermark is seeded at startup (see bootstrap.seed_default_watermark).
    """
    if not settings.WATERMARK_ENABLED:
        return None
    return db.scalar(
        select(Watermark)
        .where(Watermark.enabled.is_(True))
        .order_by(Watermark.created_at.asc())
        .limit(1)
    )


def overlay_position(
    position: str,
    frame_w: int,
    frame_h: int,
    overlay_w: int,
    overlay_h: int,
    margin: int,
) -> tuple[int, int]:
    """Return (x, y) for an overlay anchored at ``position`` (9 positions)."""
    position = (position or _DEFAULT_POSITION).strip().lower()

    if "center" in position:
        x = (frame_w - overlay_w) // 2
    elif "right" in position:
        x = frame_w - overlay_w - margin
    else:
        x = margin

    if position.startswith("middle"):
        y = (frame_h - overlay_h) // 2
    elif position.startswith("bottom"):
        y = frame_h - overlay_h - margin
    else:
        y = margin
    return x, y


def _load_font(size_px: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size_px)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size_px)
    except TypeError:  # pragma: no cover - very old Pillow
        return ImageFont.load_default()


def _apply_opacity(img: Image.Image, opacity: float) -> Image.Image:
    alpha = img.split()[-1]
    alpha = alpha.point(lambda a: int(a * opacity))
    img.putalpha(alpha)
    return img


def _render_text_watermark(
    text: str,
    opacity: float,
    size_px: int,
    out_path: Path,
) -> Path:
    font = _load_font(size_px)
    probe = Image.new("RGBA", (1, 1))
    bbox = ImageDraw.Draw(probe).textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad = max(8, int(size_px * 0.4))
    offset_x = pad - bbox[0]
    offset_y = pad - bbox[1]

    canvas = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))

    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text(
        (offset_x + 2, offset_y + 2),
        text,
        font=font,
        fill=(0, 0, 0, int(120 * opacity)),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=2))
    canvas = Image.alpha_composite(canvas, shadow)

    ImageDraw.Draw(canvas).text(
        (offset_x, offset_y),
        text,
        font=font,
        fill=(255, 255, 255, int(255 * opacity)),
    )
    canvas.save(out_path, "PNG")
    return out_path


def _render_image_watermark(
    watermark: Watermark,
    opacity: float,
    size_px: int,
    out_path: Path,
) -> Path | None:
    image_url = (watermark.image_url or "").strip()
    if not image_url:
        return None
    try:
        img = Image.open(image_url)
        img = img.convert("RGBA")
    except OSError:
        return None
    img.thumbnail((size_px, size_px), Image.LANCZOS)
    _apply_opacity(img, opacity)
    img.save(out_path, "PNG")
    return out_path


def render_watermark(
    watermark: Watermark,
    canvas_w: int,
    canvas_h: int,
    out_path: Path,
) -> Path:
    """Render the watermark as a standalone RGBA PNG sized for ``canvas_w``/``canvas_h``.

    Opacity is baked into the PNG alpha channel so both the Pillow and FFmpeg
    pipelines can composite it without engine-specific opacity handling.
    """
    opacity = watermark.opacity if watermark.opacity is not None else _DEFAULT_OPACITY
    opacity = max(0.05, min(1.0, opacity))
    size_percent = (
        watermark.size_percent
        if watermark.size_percent is not None
        else _DEFAULT_SIZE_PERCENT
    )
    size_px = max(12, int(round(min(canvas_w, canvas_h) * size_percent / 100)))

    if watermark.type == "image":
        rendered = _render_image_watermark(watermark, opacity, size_px, out_path)
        if rendered is not None:
            return rendered

    text = (watermark.text or "").strip() or "HD Guru"
    return _render_text_watermark(text, opacity, size_px, out_path)
