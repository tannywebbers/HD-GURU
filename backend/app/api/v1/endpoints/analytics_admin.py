from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.api.responses import standard_responses
from app.core.database import get_db
from app.core.exceptions import AppError
from app.models.analytics import Analytics
from app.models.enums import Permission
from app.models.traffic_stat import TrafficStat
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsEventItem,
    AnalyticsEventPage,
    AnalyticsOverview,
    AnalyticsTimePoint,
    AnalyticsTimeseries,
    AnalyticsTopItem,
    AnalyticsTopList,
)
from app.services import analytics_service
from app.services.ads.service import analytics_retention_days
from app.utils.pagination import paginate

router = APIRouter(prefix="/admin/analytics", tags=["Admin · Analytics"])

_OVERVIEW_CARD_COUNTERS = (
    "page_views",
    "uploads",
    "uploads_completed",
    "get_hd_clicks",
    "whatsapp_opens",
    "whatsapp_requests",
    "media_deliveries",
    "errors",
    "ad_impressions",
    "ad_clicks",
    "ad_load_failures",
)


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _since(days: int) -> dt.datetime:
    return _now() - dt.timedelta(days=days)


def _sum(db: Session, column, start: dt.datetime) -> int:
    return (
        db.scalar(select(func.sum(column)).where(TrafficStat.stat_date >= start.date()))
        or 0
    )


@router.get(
    "/overview",
    response_model=AnalyticsOverview,
    summary="Analytics overview cards",
    description=(
        "Today / 7 days / 30 days cards for visitors, page views, uploads, "
        "GET HD clicks, WhatsApp and delivery funnels, errors and ad events."
    ),
    responses=standard_responses(),
)
def analytics_overview(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_admin(permission=Permission.ANALYTICS_VIEW)),
    db: Session = Depends(get_db),
) -> AnalyticsOverview:
    start = _since(days)
    visitors = _sum(db, TrafficStat.sessions, start)
    counts = {
        counter: _sum(db, getattr(TrafficStat, counter), start)
        for counter in _OVERVIEW_CARD_COUNTERS
    }
    uploads = counts["uploads"]
    completed = counts["uploads_completed"]
    processing_rate = (
        round(completed / uploads * 100, 2)
        if uploads > 0
        else None
    )
    return AnalyticsOverview(
        range_days=days,
        visitors=visitors,
        page_views=counts["page_views"],
        uploads=uploads,
        uploads_completed=completed,
        get_hd_clicks=counts["get_hd_clicks"],
        whatsapp_opens=counts["whatsapp_opens"],
        whatsapp_requests=counts["whatsapp_requests"],
        media_deliveries=counts["media_deliveries"],
        errors=counts["errors"],
        processing_rate=processing_rate,
        ad_impressions=counts["ad_impressions"],
        ad_clicks=counts["ad_clicks"],
        ad_load_failures=counts["ad_load_failures"],
    )


@router.get(
    "/timeseries",
    response_model=AnalyticsTimeseries,
    summary="Visitors / uploads / clicks / deliveries over time",
    description="Per-day aggregates for the requested range (bucketed by day).",
    responses=standard_responses(),
)
def analytics_timeseries(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_admin(permission=Permission.ANALYTICS_VIEW)),
    db: Session = Depends(get_db),
) -> AnalyticsTimeseries:
    start = _since(days)
    rows = db.execute(
        select(
            TrafficStat.stat_date,
            func.sum(TrafficStat.sessions),
            func.sum(TrafficStat.page_views),
            func.sum(TrafficStat.uploads),
            func.sum(TrafficStat.get_hd_clicks),
            func.sum(TrafficStat.media_deliveries),
            func.sum(TrafficStat.errors),
        )
        .where(TrafficStat.stat_date >= start.date())
        .group_by(TrafficStat.stat_date)
        .order_by(TrafficStat.stat_date)
    ).all()
    points = [
        AnalyticsTimePoint(
            date=row.stat_date.isoformat(),
            visitors=int(row[1] or 0),
            page_views=int(row[2] or 0),
            uploads=int(row[3] or 0),
            get_hd_clicks=int(row[4] or 0),
            media_deliveries=int(row[5] or 0),
            errors=int(row[6] or 0),
        )
        for row in rows
    ]
    return AnalyticsTimeseries(points=points)


@router.get(
    "/events",
    response_model=AnalyticsEventPage,
    summary="Raw analytics events",
    description=(
        "Paginated raw event log (subject to the configured retention window). "
        "Useful for debugging the funnel; aggregate endpoints are preferred."
    ),
    responses=standard_responses(),
)
def analytics_events(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    event: str | None = Query(None, max_length=64),
    page_path: str | None = Query(None, max_length=128),
    current_user: User = Depends(require_admin(permission=Permission.ANALYTICS_VIEW)),
    db: Session = Depends(get_db),
) -> AnalyticsEventPage:
    stmt = select(Analytics)
    if event:
        stmt = stmt.where(Analytics.event_type == event)
    if page_path:
        stmt = stmt.where(Analytics.page == page_path)
    stmt = stmt.order_by(Analytics.created_at.desc())
    result = paginate(db, stmt, page=page, per_page=per_page)
    return AnalyticsEventPage(
        items=[
            AnalyticsEventItem(
                id=row.id,
                event_type=row.event_type,
                session_id=row.session_id,
                page=row.page,
                device=row.device,
                browser=row.browser,
                os=row.os,
                country=row.country,
                referrer_category=row.referrer_category,
                created_at=row.created_at,
            )
            for row in result.items
        ],
        total=result.total,
        page=result.page,
        per_page=result.per_page,
        pages=result.pages,
    )


def _top_list(
    db: Session, column, start: dt.datetime, limit: int
) -> AnalyticsTopList:
    rows = db.execute(
        select(column, func.sum(TrafficStat.events_count))
        .where(TrafficStat.stat_date >= start.date())
        .group_by(column)
        .order_by(func.sum(TrafficStat.events_count).desc())
        .limit(limit)
    ).all()
    return AnalyticsTopList(
        items=[
            AnalyticsTopItem(key=key or "unknown", count=int(count or 0))
            for key, count in rows
        ]
    )


@router.get(
    "/top-pages",
    response_model=AnalyticsTopList,
    summary="Top pages",
    responses=standard_responses(),
)
def top_pages(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(require_admin(permission=Permission.ANALYTICS_VIEW)),
    db: Session = Depends(get_db),
) -> AnalyticsTopList:
    return _top_list(db, TrafficStat.page_url, _since(days), limit)


@router.get(
    "/devices",
    response_model=AnalyticsTopList,
    summary="Device / browser / OS distribution",
    description="Pass ?dimension=device|browser|os.",
    responses=standard_responses(),
)
def devices(
    days: int = Query(30, ge=1, le=365),
    dimension: str = Query("device", pattern="^(device|browser|os)$"),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(require_admin(permission=Permission.ANALYTICS_VIEW)),
    db: Session = Depends(get_db),
) -> AnalyticsTopList:
    column = {
        "device": TrafficStat.device,
        "browser": TrafficStat.browser,
        "os": TrafficStat.os,
    }[dimension]
    return _top_list(db, column, _since(days), limit)


@router.get(
    "/referrers",
    response_model=AnalyticsTopList,
    summary="Top referrer categories",
    responses=standard_responses(),
)
def referrers(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(require_admin(permission=Permission.ANALYTICS_VIEW)),
    db: Session = Depends(get_db),
) -> AnalyticsTopList:
    return _top_list(db, TrafficStat.referrer, _since(days), limit)


@router.post(
    "/retention/run",
    response_model=dict,
    summary="Purge expired analytics rows",
    description=(
        "Deletes raw analytics/ad event rows older than the configured "
        "retention. Aggregated daily stats are kept."
    ),
    responses=standard_responses(),
)
def run_retention(
    current_user: User = Depends(require_admin(permission=Permission.ANALYTICS_VIEW)),
    db: Session = Depends(get_db),
):
    return analytics_service.run_retention(db, days=analytics_retention_days(db))
