from __future__ import annotations

"""Advertising configuration service.

Turns the ad provider/placement tables into a small, safe configuration the
public frontend can consume, and records ad analytics (impressions, clicks,
load failures) without ever storing personal data.
"""

import hashlib
import json
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ad_event import AdEvent
from app.models.ad_placement import AdPlacement, AdPlacementProvider
from app.models.ad_provider import AdProvider
from app.models.setting import Setting
from app.models.enums import AdEventType
from app.services.ads.adapters import build_render, validate_provider


# --- config-driven settings -------------------------------------------------


def get_setting_value(db: Session, key: str, default):
    row = db.scalar(select(Setting).where(Setting.key == key))
    if row is None:
        return default
    return row.value


def ads_enabled(db: Session) -> bool:
    return bool(get_setting_value(db, "ads.enabled", settings.ADS_ENABLED))


def analytics_enabled(db: Session) -> bool:
    return bool(
        get_setting_value(db, "analytics.enabled", settings.ANALYTICS_ENABLED)
    )


def analytics_retention_days(db: Session) -> int:
    value = get_setting_value(db, "analytics.retention_days", settings.ANALYTICS_RETENTION_DAYS)
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return settings.ANALYTICS_RETENTION_DAYS


def default_behavior(db: Session) -> str:
    value = get_setting_value(
        db, "ads.default_placement_behavior", settings.ADS_DEFAULT_PLACEMENT_BEHAVIOR
    )
    return value if value in {"lazy", "eager"} else "lazy"


# --- public configuration ---------------------------------------------------


def public_config(db: Session) -> dict:
    """The safe, minimal ad configuration sent to the public frontend.

    Contains only public identifiers and generated render snippets. Secrets
    (api_key etc.) are never included.
    """
    enabled = ads_enabled(db)
    placements: dict[str, dict] = {}
    if enabled:
        rows = db.scalars(
            select(AdPlacement)
            .where(AdPlacement.enabled.is_(True))
            .order_by(AdPlacement.name)
        ).all()
        default_bev = default_behavior(db)
        for placement in rows:
            slot_map = _placement_slots(db, placement)
            if not slot_map:
                continue
            placements[placement.name] = {
                "name": placement.name,
                "label": placement.label,
                "behavior": placement.behavior or default_bev,
                "width": placement.width,
                "height": placement.height,
                "responsive": placement.responsive,
                "slots": slot_map,
            }
    payload = {"enabled": enabled, "placements": placements}
    payload["version"] = _config_version(payload)
    return payload


def _placement_slots(db: Session, placement: AdPlacement) -> list[dict]:
    rows = db.execute(
        select(AdPlacementProvider, AdProvider)
        .join(AdProvider, AdProvider.id == AdPlacementProvider.provider_id)
        .where(
            AdPlacementProvider.placement_id == placement.id,
            AdPlacementProvider.enabled.is_(True),
            AdProvider.enabled.is_(True),
        )
        .order_by(AdPlacementProvider.priority.asc())
    ).all()
    slots: list[dict] = []
    for assoc, provider in rows:
        render = build_render(provider)
        if not _render_ready(render):
            continue
        assoc_config = assoc.config or {}
        width = assoc_config.get("width", placement.width)
        height = assoc_config.get("height", placement.height)
        responsive = bool(assoc_config.get("responsive", placement.responsive))
        slots.append(
            {
                "provider_id": str(provider.id),
                "name": provider.name,
                "type": render["kind"],
                "frequency": assoc.frequency,
                "width": width,
                "height": height,
                "responsive": responsive,
                "render": render,
            }
        )
    return slots


def _render_ready(render: dict) -> bool:
    if render.get("kind") in {"script", "html", "custom"}:
        return bool((render.get("content") or "").strip())
    if render.get("kind") == "iframe":
        return bool((render.get("src") or "").strip())
    return False


def _config_version(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:12]


# --- ad events --------------------------------------------------------------


def record_ad_event(
    db: Session,
    *,
    event_type: AdEventType | str,
    placement_name: str,
    session_id: str | None,
    page: str | None,
    provider_id: uuid.UUID | None = None,
) -> None:
    """Record a raw ad event (best-effort; never raises into the caller)."""
    try:
        provider_name = None
        if provider_id is not None:
            provider = db.get(AdProvider, provider_id)
            provider_name = provider.name if provider is not None else None
        event_type_str = (
            event_type.value if isinstance(event_type, AdEventType) else str(event_type)
        )
        db.add(
            AdEvent(
                event_type=event_type_str,
                provider_id=provider_id,
                provider_name=provider_name,
                placement_name=placement_name,
                session_id=session_id,
                page=page,
            )
        )
        db.commit()
    except Exception:
        db.rollback()


# --- overview ---------------------------------------------------------------


def ads_overview(db: Session) -> dict:
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    providers_total = db.scalar(select(func.count()).select_from(AdProvider)) or 0
    providers_enabled = (
        db.scalar(
            select(func.count())
            .select_from(AdProvider)
            .where(AdProvider.enabled.is_(True))
        )
        or 0
    )
    placements_total = db.scalar(select(func.count()).select_from(AdPlacement)) or 0
    placements_enabled = (
        db.scalar(
            select(func.count())
            .select_from(AdPlacement)
            .where(AdPlacement.enabled.is_(True))
        )
        or 0
    )
    slots_total = (
        db.scalar(
            select(func.count())
            .select_from(AdPlacementProvider)
            .where(AdPlacementProvider.enabled.is_(True))
        )
        or 0
    )

    def _counts(since=None):
        stmt = select(AdEvent.event_type, func.count()).group_by(AdEvent.event_type)
        if since is not None:
            stmt = stmt.where(AdEvent.created_at >= since)
        return dict(db.execute(stmt).all())

    total = _counts()
    today = _counts(day_start)
    impressions = total.get(AdEventType.IMPRESSION.value, 0)
    clicks = total.get(AdEventType.CLICK.value, 0)
    failures = total.get(AdEventType.LOAD_FAILURE.value, 0)
    ctr = round((clicks / impressions * 100), 2) if impressions else 0.0

    return {
        "enabled": ads_enabled(db),
        "providers_total": providers_total,
        "providers_enabled": providers_enabled,
        "placements_total": placements_total,
        "placements_enabled": placements_enabled,
        "active_slots": slots_total,
        "impressions": impressions,
        "impressions_today": today.get(AdEventType.IMPRESSION.value, 0),
        "clicks": clicks,
        "clicks_today": today.get(AdEventType.CLICK.value, 0),
        "load_failures": failures,
        "load_failures_today": today.get(AdEventType.LOAD_FAILURE.value, 0),
        "ctr": ctr,
        "default_behavior": default_behavior(db),
        "providers": [
            {
                "id": str(p.id),
                "name": p.name,
                "provider_type": p.provider_type,
                "enabled": p.enabled,
            }
            for p in db.scalars(
                select(AdProvider).order_by(AdProvider.name)
            ).all()
        ],
    }


# --- test helper ------------------------------------------------------------


def test_provider_config(provider: AdProvider) -> dict:
    render = build_render(provider)
    missing = validate_provider(provider)
    return {
        "ok": not missing,
        "missing": missing,
        "render_kind": render.get("kind"),
        "render_ready": _render_ready(render),
        "snippet_preview": (render.get("content") or render.get("src") or "")[:400],
    }
