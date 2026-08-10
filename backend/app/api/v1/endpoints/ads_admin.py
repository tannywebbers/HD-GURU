from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.api.responses import standard_responses
from app.core.database import get_db
from app.core.exceptions import AppError
from app.models.ad_event import AdEvent
from app.models.ad_placement import AdPlacement, AdPlacementProvider
from app.models.ad_provider import AdProvider
from app.models.enums import AdEventType, AdProviderType, Permission
from app.models.user import User
from app.schemas.ads import (
    AdPlacementCreate,
    AdPlacementItem,
    AdPlacementReorder,
    AdPlacementUpdate,
    AdProviderCreate,
    AdProviderItem,
    AdProviderUpdate,
    AdSlotIn,
    AdSlotItem,
)
from app.services import audit_service
from app.services.ads import service as ads_service

router = APIRouter(prefix="/admin/ads", tags=["Admin · Ads"])

_AD_PROVIDER_TYPES = tuple(t.value for t in AdProviderType)
_FREQUENCIES = {"every_page", "every_session", "once_per_session", "interval"}


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _admin_log(
    db: Session,
    request: Request,
    actor: User,
    *,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict | None = None,
    result: str = "success",
) -> None:
    ip, user_agent = audit_service.client_meta(request)
    audit_service.log_action(
        db,
        action=action,
        actor=actor,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip,
        user_agent=user_agent,
        result=result,
    )


def _provider_item(p: AdProvider) -> AdProviderItem:
    return AdProviderItem(
        id=p.id,
        name=p.name,
        provider_type=p.provider_type,
        base_url=p.base_url,
        publisher_id=p.publisher_id,
        zone_id=p.zone_id,
        site_id=p.site_id,
        placement_config=p.placement_config or {},
        custom_script=p.custom_script,
        click_through_url=p.click_through_url,
        enabled=p.enabled,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _placement_item(db: Session, pl: AdPlacement) -> AdPlacementItem:
    slots: list[AdSlotItem] = []
    rows = db.execute(
        select(AdPlacementProvider, AdProvider)
        .join(AdProvider, AdProvider.id == AdPlacementProvider.provider_id)
        .where(AdPlacementProvider.placement_id == pl.id)
        .order_by(AdPlacementProvider.priority.asc())
    ).all()
    for assoc, provider in rows:
        slots.append(
            AdSlotItem(
                id=assoc.id,
                provider_id=provider.id,
                provider_name=provider.name,
                provider_enabled=provider.enabled,
                priority=assoc.priority,
                frequency=assoc.frequency,
                enabled=assoc.enabled,
                config=assoc.config or {},
            )
        )
    return AdPlacementItem(
        id=pl.id,
        name=pl.name,
        label=pl.label,
        enabled=pl.enabled,
        width=pl.width,
        height=pl.height,
        responsive=pl.responsive,
        behavior=pl.behavior,
        slots=slots,
        created_at=pl.created_at,
        updated_at=pl.updated_at,
    )


# --- overview ---------------------------------------------------------------


@router.get(
    "/overview",
    response_model=dict,
    summary="Ads overview",
    description=(
        "Active provider/placement/slot counts, impression/click/failure totals "
        "and CTR, plus the configured provider list."
    ),
    responses=standard_responses(),
)
def ads_overview(
    current_user: User = Depends(require_admin(permission=Permission.ADS_VIEW)),
    db: Session = Depends(get_db),
):
    return ads_service.ads_overview(db)


# --- providers --------------------------------------------------------------


@router.get(
    "/providers",
    response_model=list[AdProviderItem],
    summary="List ad providers",
    responses=standard_responses(),
)
def list_providers(
    current_user: User = Depends(require_admin(permission=Permission.ADS_VIEW)),
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(AdProvider).order_by(AdProvider.name)).all()
    return [_provider_item(p) for p in rows]


@router.post(
    "/providers",
    response_model=AdProviderItem,
    status_code=201,
    summary="Create an ad provider",
    responses=standard_responses(),
)
def create_provider(
    payload: AdProviderCreate,
    request: Request,
    current_user: User = Depends(require_admin(permission=Permission.ADS_MANAGE)),
    db: Session = Depends(get_db),
) -> AdProviderItem:
    name = payload.name.strip()
    if db.scalar(select(AdProvider).where(AdProvider.name == name)):
        raise AppError(409, "NAME_EXISTS", "A provider with this name exists.")
    provider = AdProvider(
        name=name,
        provider_type=payload.provider_type,
        base_url=payload.base_url,
        publisher_id=payload.publisher_id,
        zone_id=payload.zone_id,
        site_id=payload.site_id,
        placement_config=payload.placement_config or {},
        custom_script=payload.custom_script,
        click_through_url=payload.click_through_url,
        enabled=payload.enabled,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    _admin_log(
        db,
        request,
        current_user,
        action="admin.ad_provider_created",
        resource_type="ad_provider",
        resource_id=str(provider.id),
        details={"name": provider.name, "type": provider.provider_type},
    )
    return _provider_item(provider)


@router.get(
    "/providers/{provider_id}",
    response_model=AdProviderItem,
    summary="Get an ad provider",
    responses=standard_responses(),
)
def get_provider(
    provider_id: uuid.UUID,
    current_user: User = Depends(require_admin(permission=Permission.ADS_VIEW)),
    db: Session = Depends(get_db),
) -> AdProviderItem:
    provider = db.get(AdProvider, provider_id)
    if provider is None:
        raise AppError(404, "PROVIDER_NOT_FOUND", "Ad provider not found.")
    return _provider_item(provider)


@router.put(
    "/providers/{provider_id}",
    response_model=AdProviderItem,
    summary="Update an ad provider",
    responses=standard_responses(),
)
def update_provider(
    provider_id: uuid.UUID,
    payload: AdProviderUpdate,
    request: Request,
    current_user: User = Depends(require_admin(permission=Permission.ADS_MANAGE)),
    db: Session = Depends(get_db),
) -> AdProviderItem:
    provider = db.get(AdProvider, provider_id)
    if provider is None:
        raise AppError(404, "PROVIDER_NOT_FOUND", "Ad provider not found.")
    changes = payload.model_dump(exclude_none=True)
    if changes.get("name"):
        new_name = changes["name"].strip()
        clash = db.scalar(
            select(AdProvider).where(
                AdProvider.name == new_name, AdProvider.id != provider.id
            )
        )
        if clash:
            raise AppError(409, "NAME_EXISTS", "A provider with this name exists.")
        changes["name"] = new_name
    for field, value in changes.items():
        setattr(provider, field, value)
    db.commit()
    db.refresh(provider)
    _admin_log(
        db,
        request,
        current_user,
        action="admin.ad_provider_updated",
        resource_type="ad_provider",
        resource_id=str(provider.id),
        details={"name": provider.name, "changes": sorted(changes.keys())},
    )
    return _provider_item(provider)


@router.delete(
    "/providers/{provider_id}",
    status_code=204,
    summary="Delete an ad provider",
    responses=standard_responses(),
)
def delete_provider(
    provider_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_admin(permission=Permission.ADS_MANAGE)),
    db: Session = Depends(get_db),
):
    provider = db.get(AdProvider, provider_id)
    if provider is None:
        raise AppError(404, "PROVIDER_NOT_FOUND", "Ad provider not found.")
    name = provider.name
    db.execute(
        delete(AdPlacementProvider).where(
            AdPlacementProvider.provider_id == provider_id
        )
    )
    db.delete(provider)
    db.commit()
    _admin_log(
        db,
        request,
        current_user,
        action="admin.ad_provider_deleted",
        resource_type="ad_provider",
        resource_id=str(provider_id),
        details={"name": name},
    )
    return None


@router.post(
    "/providers/{provider_id}/test",
    response_model=dict,
    summary="Test an ad provider configuration",
    description=(
        "Validates the provider can produce a render snippet and reports which "
        "identifiers are still missing. Never calls the provider network."
    ),
    responses=standard_responses(),
)
def test_provider(
    provider_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_admin(permission=Permission.ADS_MANAGE)),
    db: Session = Depends(get_db),
):
    provider = db.get(AdProvider, provider_id)
    if provider is None:
        raise AppError(404, "PROVIDER_NOT_FOUND", "Ad provider not found.")
    result = ads_service.test_provider_config(provider)
    _admin_log(
        db,
        request,
        current_user,
        action="admin.ad_provider_tested",
        resource_type="ad_provider",
        resource_id=str(provider_id),
        details={"ok": result["ok"], "missing": result["missing"]},
        result="success" if result["ok"] else "failure",
    )
    return result


# --- placements -------------------------------------------------------------


@router.get(
    "/placements",
    response_model=list[AdPlacementItem],
    summary="List ad placements",
    responses=standard_responses(),
)
def list_placements(
    current_user: User = Depends(require_admin(permission=Permission.ADS_VIEW)),
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(AdPlacement).order_by(AdPlacement.name)).all()
    return [_placement_item(db, pl) for pl in rows]


@router.post(
    "/placements",
    response_model=AdPlacementItem,
    status_code=201,
    summary="Create an ad placement",
    responses=standard_responses(),
)
def create_placement(
    payload: AdPlacementCreate,
    request: Request,
    current_user: User = Depends(require_admin(permission=Permission.ADS_MANAGE)),
    db: Session = Depends(get_db),
) -> AdPlacementItem:
    if db.scalar(select(AdPlacement).where(AdPlacement.name == payload.name)):
        raise AppError(409, "NAME_EXISTS", "A placement with this name exists.")
    placement = AdPlacement(
        name=payload.name,
        label=payload.label,
        enabled=payload.enabled,
        width=payload.width,
        height=payload.height,
        responsive=payload.responsive,
        behavior=payload.behavior,
    )
    db.add(placement)
    db.flush()
    _apply_slots(db, placement, payload.slots)
    db.commit()
    db.refresh(placement)
    _admin_log(
        db,
        request,
        current_user,
        action="admin.ad_placement_created",
        resource_type="ad_placement",
        resource_id=str(placement.id),
        details={"name": placement.name, "slots": len(payload.slots)},
    )
    return _placement_item(db, placement)


@router.get(
    "/placements/{placement_id}",
    response_model=AdPlacementItem,
    summary="Get an ad placement",
    responses=standard_responses(),
)
def get_placement(
    placement_id: uuid.UUID,
    current_user: User = Depends(require_admin(permission=Permission.ADS_VIEW)),
    db: Session = Depends(get_db),
) -> AdPlacementItem:
    placement = db.get(AdPlacement, placement_id)
    if placement is None:
        raise AppError(404, "PLACEMENT_NOT_FOUND", "Ad placement not found.")
    return _placement_item(db, placement)


@router.put(
    "/placements/{placement_id}",
    response_model=AdPlacementItem,
    summary="Update an ad placement",
    responses=standard_responses(),
)
def update_placement(
    placement_id: uuid.UUID,
    payload: AdPlacementUpdate,
    request: Request,
    current_user: User = Depends(require_admin(permission=Permission.ADS_MANAGE)),
    db: Session = Depends(get_db),
) -> AdPlacementItem:
    placement = db.get(AdPlacement, placement_id)
    if placement is None:
        raise AppError(404, "PLACEMENT_NOT_FOUND", "Ad placement not found.")
    changes = payload.model_dump(exclude_none=True)
    for field, value in changes.items():
        setattr(placement, field, value)
    db.commit()
    db.refresh(placement)
    _admin_log(
        db,
        request,
        current_user,
        action="admin.ad_placement_updated",
        resource_type="ad_placement",
        resource_id=str(placement.id),
        details={"name": placement.name, "changes": sorted(changes.keys())},
    )
    return _placement_item(db, placement)


@router.delete(
    "/placements/{placement_id}",
    status_code=204,
    summary="Delete an ad placement",
    responses=standard_responses(),
)
def delete_placement(
    placement_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_admin(permission=Permission.ADS_MANAGE)),
    db: Session = Depends(get_db),
):
    placement = db.get(AdPlacement, placement_id)
    if placement is None:
        raise AppError(404, "PLACEMENT_NOT_FOUND", "Ad placement not found.")
    name = placement.name
    db.delete(placement)
    db.commit()
    _admin_log(
        db,
        request,
        current_user,
        action="admin.ad_placement_deleted",
        resource_type="ad_placement",
        resource_id=str(placement_id),
        details={"name": name},
    )
    return None


@router.put(
    "/placements/{placement_id}/slots",
    response_model=AdPlacementItem,
    summary="Replace the provider slots on a placement",
    description="Replaces the full slot list, preserving priority order given.",
    responses=standard_responses(),
)
def replace_placement_slots(
    placement_id: uuid.UUID,
    payload: list[AdSlotIn],
    request: Request,
    current_user: User = Depends(require_admin(permission=Permission.ADS_MANAGE)),
    db: Session = Depends(get_db),
) -> AdPlacementItem:
    placement = db.get(AdPlacement, placement_id)
    if placement is None:
        raise AppError(404, "PLACEMENT_NOT_FOUND", "Ad placement not found.")
    for slot in payload:
        if slot.frequency not in _FREQUENCIES:
            raise AppError(400, "INVALID_FREQUENCY", "Unknown frequency.")
        if db.get(AdProvider, slot.provider_id) is None:
            raise AppError(404, "PROVIDER_NOT_FOUND", "Unknown provider in slot.")
    _apply_slots(db, placement, payload)
    db.commit()
    _admin_log(
        db,
        request,
        current_user,
        action="admin.ad_placement_slots_updated",
        resource_type="ad_placement",
        resource_id=str(placement.id),
        details={"name": placement.name, "slots": len(payload)},
    )
    return _placement_item(db, placement)


@router.put(
    "/placements/{placement_id}/reorder",
    response_model=AdPlacementItem,
    summary="Reorder slot priority on a placement",
    description=(
        "provider_ids in priority order — the first id becomes priority 1."
    ),
    responses=standard_responses(),
)
def reorder_placement_slots(
    placement_id: uuid.UUID,
    payload: AdPlacementReorder,
    request: Request,
    current_user: User = Depends(require_admin(permission=Permission.ADS_MANAGE)),
    db: Session = Depends(get_db),
) -> AdPlacementItem:
    placement = db.get(AdPlacement, placement_id)
    if placement is None:
        raise AppError(404, "PLACEMENT_NOT_FOUND", "Ad placement not found.")
    existing = {
        assoc.provider_id: assoc
        for assoc in db.scalars(
            select(AdPlacementProvider).where(
                AdPlacementProvider.placement_id == placement_id
            )
        ).all()
    }
    if set(payload.provider_ids) != set(existing.keys()):
        raise AppError(
            400,
            "INVALID_ORDER",
            "Reorder must include exactly the placement's current providers.",
        )
    for priority, provider_id in enumerate(payload.provider_ids, start=1):
        existing[provider_id].priority = priority
    db.commit()
    _admin_log(
        db,
        request,
        current_user,
        action="admin.ad_placement_reordered",
        resource_type="ad_placement",
        resource_id=str(placement.id),
        details={"name": placement.name},
    )
    return _placement_item(db, placement)


@router.get(
    "/placements/{placement_id}/preview",
    response_model=dict,
    summary="Preview a placement",
    description=(
        "Returns the exact public config entry a placement would receive, so "
        "an admin can verify rendering before enabling it."
    ),
    responses=standard_responses(),
)
def preview_placement(
    placement_id: uuid.UUID,
    current_user: User = Depends(require_admin(permission=Permission.ADS_VIEW)),
    db: Session = Depends(get_db),
):
    placement = db.get(AdPlacement, placement_id)
    if placement is None:
        raise AppError(404, "PLACEMENT_NOT_FOUND", "Ad placement not found.")
    config = ads_service.public_config(db)
    entry = config.get("placements", {}).get(placement.name)
    if entry is None:
        return {"enabled": config.get("enabled"), "placement": None}
    return {"enabled": config.get("enabled"), "placement": entry}


# --- ad analytics -----------------------------------------------------------


@router.get(
    "/analytics",
    response_model=dict,
    summary="Ad performance analytics",
    description=(
        "Impressions, clicks and load failures over a range, optionally broken "
        "down by provider or placement. Provider policies are never bypassed — "
        "this reports events our own frontend observed."
    ),
    responses=standard_responses(),
)
def ad_analytics(
    days: int = Query(30, ge=1, le=365),
    group: str = Query("provider", pattern="^(provider|placement|day)$"),
    current_user: User = Depends(require_admin(permission=Permission.ANALYTICS_VIEW)),
    db: Session = Depends(get_db),
):
    since = _now() - dt.timedelta(days=days)
    stmt = select(
        AdEvent.event_type, func.count(AdEvent.id)
    ).where(AdEvent.created_at >= since.replace(tzinfo=None))
    totals = dict(db.execute(stmt.group_by(AdEvent.event_type)).all())

    def _impressions(rows: list) -> int:
        return sum(r.get("impression", 0) for r in rows)

    if group == "day":
        rows = db.execute(
            select(
                func.date(AdEvent.created_at).label("date"),
                AdEvent.event_type,
                func.count(AdEvent.id),
            )
            .where(AdEvent.created_at >= since.replace(tzinfo=None))
            .group_by("date", AdEvent.event_type)
            .order_by("date")
        ).all()
        series: dict[str, dict] = {}
        for date, event_type, count in rows:
            point = series.setdefault(str(date), {"impression": 0, "click": 0, "load_failure": 0})
            point[event_type] = point.get(event_type, 0) + count
        by_group = [{"key": d, **series[d]} for d in sorted(series)]
    else:
        col = AdEvent.provider_name if group == "provider" else AdEvent.placement_name
        rows = db.execute(
            select(col, AdEvent.event_type, func.count(AdEvent.id))
            .where(AdEvent.created_at >= since.replace(tzinfo=None))
            .group_by(col, AdEvent.event_type)
            .order_by(col)
        ).all()
        merged: dict[str, dict] = {}
        for key, event_type, count in rows:
            point = merged.setdefault(key or "unknown", {"impression": 0, "click": 0, "load_failure": 0})
            point[event_type] = point.get(event_type, 0) + count
        by_group = [
            {"key": k, **v, "ctr": _ctr(v)}
            for k, v in sorted(merged.items(), key=lambda kv: _impressions([kv[1]]), reverse=True)
        ]

    total_impressions = totals.get(AdEventType.IMPRESSION.value, 0)
    total_clicks = totals.get(AdEventType.CLICK.value, 0)
    total_failures = totals.get(AdEventType.LOAD_FAILURE.value, 0)
    return {
        "days": days,
        "totals": {
            "impressions": total_impressions,
            "clicks": total_clicks,
            "load_failures": total_failures,
            "ctr": _ctr({"impression": total_impressions, "click": total_clicks}),
        },
        "group": group,
        "items": by_group,
    }


def _ctr(point: dict) -> float:
    impressions = point.get("impression", 0)
    clicks = point.get("click", 0)
    return round((clicks / impressions * 100), 2) if impressions else 0.0


def _apply_slots(db: Session, placement: AdPlacement, slots: list[AdSlotIn]) -> None:
    for existing in list(placement.slots):
        db.delete(existing)
    db.flush()
    for index, slot in enumerate(slots, start=1):
        db.add(
            AdPlacementProvider(
                placement_id=placement.id,
                provider_id=slot.provider_id,
                priority=slot.priority,
                frequency=slot.frequency,
                enabled=slot.enabled,
                config=slot.config or {},
            )
        )
    db.flush()
