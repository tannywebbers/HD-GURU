from __future__ import annotations

import datetime as dt

_OBJECT_KINDS = {"original", "processed", "thumbnails"}


def media_object_key(
    kind: str,
    public_id: str,
    extension: str,
    when: dt.datetime | None = None,
) -> str:
    """Build an organized object key for a media artifact.

    Keys are based on the media public ID (never the original filename) and
    grouped by kind and upload month so buckets stay navigable:

        media/original/2026/08/HD7K2P9X4M8QW3ZT.mp4
        media/processed/2026/08/HD7K2P9X4M8QW3ZT.mp4
        media/thumbnails/2026/08/HD7K2P9X4M8QW3ZT.jpg
    """
    kind = kind.strip().lower()
    if kind not in _OBJECT_KINDS:
        raise ValueError(f"Unknown media object kind: {kind!r}")
    when = when or dt.datetime.now(dt.timezone.utc)
    ext = extension.strip().lstrip(".").lower() or "bin"
    return f"media/{kind}/{when:%Y}/{when:%m}/{public_id}.{ext}"
