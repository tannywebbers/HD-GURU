from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from app.core.config import settings
from app.models.watermark import Watermark
from app.services.processing.common import (
    MediaProcessingError,
    ProcessingResult,
    prepare_watermark,
    target_video_dimensions,
)

_ENCODE_TIMEOUT_SECONDS = 3600
_CRF_START = 20
_CRF_STEP = 2
_MAX_ENCODE_ATTEMPTS = 6
_THUMBNAIL_MAX_WIDTH = 320

_AUDIO_BITRATE = "96k"


def probe_video(path: str) -> dict:
    ffprobe = _binary("ffprobe")
    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=_ENCODE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise MediaProcessingError("Video analysis timed out.") from exc
    if result.returncode != 0 or not result.stdout.strip():
        raise MediaProcessingError(
            "The video could not be read. It may be corrupted or unsupported."
        )
    return json.loads(result.stdout)


def process_video(
    input_path: str,
    temp_dir: Path,
    watermark: Watermark | None,
) -> ProcessingResult:
    """Re-encode a video to an H.264/AAC MP4 sized for WhatsApp.

    Probes the source, computes target dimensions within the portrait /
    landscape / square caps, then encodes with a CRF loop that re-encodes at a
    higher CRF (lower quality) until the output is under the size target or the
    quality floor (``MIN_VIDEO_QUALITY``) is reached. Never loops forever.
    """
    temp_dir = Path(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    info = probe_video(input_path)
    video_stream = _first_stream(info, "video")
    if video_stream is None:
        raise MediaProcessingError("The file contains no video stream.")

    source_w = int(video_stream.get("width") or 0)
    source_h = int(video_stream.get("height") or 0)
    rotation = _rotation(video_stream)
    if rotation in (90, 270):
        source_w, source_h = source_h, source_w

    out_w, out_h = target_video_dimensions(source_w, source_h)

    duration = _format_duration(info)
    has_audio = _first_stream(info, "audio") is not None

    wm_asset = prepare_watermark(
        watermark, out_w, out_h, temp_dir / "watermark.png"
    )

    crf = _CRF_START
    final_path: Path | None = None
    for attempt in range(_MAX_ENCODE_ATTEMPTS):
        candidate = temp_dir / f"optimized_{attempt}.mp4"
        args = _build_encode_args(
            input_path=input_path,
            output=str(candidate),
            width=out_w,
            height=out_h,
            crf=crf,
            has_audio=has_audio,
            duration=duration,
            wm_asset=wm_asset,
        )
        _run_ffmpeg(args)
        size = candidate.stat().st_size
        under_target = size <= settings.max_video_output_size_bytes
        if under_target or crf >= settings.MIN_VIDEO_QUALITY:
            final_path = candidate
            break
        crf += _CRF_STEP
        candidate.unlink(missing_ok=True)

    if final_path is None:
        final_path = temp_dir / f"optimized_{_MAX_ENCODE_ATTEMPTS - 1}.mp4"
        raise MediaProcessingError(
            "Could not compress the video to the target size within quality limits."
        )

    thumbnail_path = temp_dir / "thumbnail.jpg"
    _extract_thumbnail(input_path, thumbnail_path, duration)

    return ProcessingResult(
        output_path=str(final_path),
        output_filename="optimized.mp4",
        thumbnail_path=str(thumbnail_path),
        mime_type="video/mp4",
        extension="mp4",
        width=out_w,
        height=out_h,
        duration=duration,
        file_size=final_path.stat().st_size,
        watermark_ref=wm_asset.ref if wm_asset is not None else None,
    )


def _build_encode_args(
    *,
    input_path: str,
    output: str,
    width: int,
    height: int,
    crf: int,
    has_audio: bool,
    duration: float | None,
    wm_asset,
) -> list[str]:
    args = ["-y", "-i", input_path]

    video_args: list[str] = [
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
    ]

    if duration:
        # Constrain the encoder to the size budget derived from the duration.
        bitrate_kbps = int(
            settings.max_video_output_size_bytes * 8 / duration / 1000
        )
        if bitrate_kbps > 200:
            video_args += ["-maxrate", f"{bitrate_kbps}k", "-bufsize", f"{2 * bitrate_kbps}k"]

    if wm_asset is not None:
        args += ["-i", str(wm_asset.png_path)]
        filter_complex = (
            f"[1:v]format=rgba[wm];"
            f"[0:v]scale={width}:{height},format=yuv420p[base];"
            f"[base][wm]overlay=x={wm_asset.x}:y={wm_asset.y}[vout]"
        )
        args += ["-filter_complex", filter_complex, "-map", "[vout]"]
    else:
        args += ["-vf", f"scale={width}:{height}"]

    if has_audio:
        args += ["-map", "0:a?", "-c:a", "aac", "-b:a", _AUDIO_BITRATE, "-ac", "2", "-shortest"]
    else:
        args += ["-an"]

    args += video_args
    args += [output]
    return args


def _run_ffmpeg(args: list[str]) -> None:
    ffmpeg = _binary("ffmpeg")
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=_ENCODE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise MediaProcessingError("Video encoding timed out.") from exc
    if result.returncode != 0:
        detail = (result.stderr or "").strip().splitlines()
        tail = " | ".join(detail[-3:]) if detail else "unknown ffmpeg error"
        raise MediaProcessingError(f"Video encoding failed: {tail[:300]}")


def _extract_thumbnail(
    input_path: str,
    out_path: Path,
    duration: float | None,
) -> None:
    seek = 0.0
    if duration:
        seek = min(1.0, duration / 2)
    args = [
        "-y",
        "-ss",
        f"{seek:.3f}",
        "-i",
        input_path,
        "-frames:v",
        "1",
        "-vf",
        f"scale='min({_THUMBNAIL_MAX_WIDTH},iw)':-2",
        str(out_path),
    ]
    _run_ffmpeg(args)


def _binary(name: str) -> str:
    binary = shutil.which(name)
    if not binary:
        raise MediaProcessingError(
            f"'{name}' is not installed. The video pipeline requires FFmpeg."
        )
    return binary


def _first_stream(info: dict, codec_type: str) -> dict | None:
    for stream in info.get("streams", []):
        if stream.get("codec_type") == codec_type:
            return stream
    return None


def _rotation(stream: dict) -> int:
    tags = stream.get("tags") or {}
    if "rotate" in tags:
        try:
            return int(tags["rotate"])
        except (TypeError, ValueError):
            return 0
    for side_data in stream.get("side_data_list") or []:
        if side_data.get("rotation") is not None:
            return int(side_data["rotation"])
    return 0


def _format_duration(info: dict) -> float | None:
    try:
        value = info.get("format", {}).get("duration")
        return float(value) if value else None
    except (TypeError, ValueError):
        return None
