from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.responses import standard_responses
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import get_rate_limiter
from app.models.enums import AdEventType
from app.schemas.ads import AdEventIn, AnalyticsEventIn, IngestResult
from app.services import analytics_service
from app.services.ads import service as ads_service

router = APIRouter(prefix="/ads", tags=["Ads"])
analytics_router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/config",
    response_model=dict,
    summary="Public ad configuration",
    description=(
        "Safe ad configuration for the public frontend: enabled placements "
        "with their prioritized provider slots and render snippets. Contains "
        "only public identifiers — never API keys or credentials."
    ),
    responses=standard_responses(),
)
def public_ad_config(
    request: Request,
    db: Session = Depends(get_db),
):
    return ads_service.public_config(db)


@router.post(
    "/event",
    response_model=IngestResult,
    summary="Record an ad impression/click/failure",
    description=(
        "Rate-limited, bot-filtered ingestion of ad interaction events. "
        "Aggregates only; no personal data is stored."
    ),
    responses=standard_responses({200: {"description": "Accepted"}}),
)
def record_ad_event(
    payload: AdEventIn,
    request: Request,
    db: Session = Depends(get_db),
) -> IngestResult:
    if is_bot(request):
        return IngestResult(ok=True)
    if not rate_allow(
        f"adevents:{analytics_service.client_ip_hash(request)}",
        settings.AD_EVENTS_PER_MINUTE,
    ):
        from app.core.exceptions import AppError

        raise AppError(429, "RATE_LIMITED", "Too many ad events. Please slow down.")

    analytics_service.track_ad_event(
        db,
        placement=payload.placement,
        page=payload.page,
        device=ua(request)[0],
        browser=ua(request)[1],
        os=ua(request)[2],
        country=analytics_service.client_country(request),
        event=payload.event_type,
    )
    ads_service.record_ad_event(
        db,
        event_type=AdEventType(payload.event_type),
        placement_name=payload.placement,
        session_id=payload.session_id,
        page=payload.page,
        provider_id=payload.provider_id,
    )
    return IngestResult(ok=True)


@analytics_router.post(
    "/events",
    response_model=IngestResult,
    summary="Record a generic analytics event",
    description=(
        "Rate-limited, bot-filtered analytics ingestion for page views, upload "
        "funnel steps, GET HD clicks, WhatsApp opens and delivery events. "
        "Anonymous session ids only; raw IPs are never stored."
    ),
    responses=standard_responses({200: {"description": "Accepted"}}),
)
def record_analytics_event(
    payload: AnalyticsEventIn,
    request: Request,
    db: Session = Depends(get_db),
) -> IngestResult:
    if is_bot(request):
        return IngestResult(ok=True)
    if not rate_allow(
        f"analytics:{analytics_service.client_ip_hash(request)}",
        settings.ANALYTICS_EVENTS_PER_MINUTE,
    ):
        from app.core.exceptions import AppError

        raise AppError(429, "RATE_LIMITED", "Too many events. Please slow down.")

    if payload.event == "page_view" and payload.session_id:
        analytics_service.upsert_session(
            db,
            session_id=payload.session_id,
            page=payload.page,
            device=ua(request)[0],
            browser=ua(request)[1],
            os=ua(request)[2],
            country=analytics_service.client_country(request),
            referrer=analytics_service.referrer_category(payload.referrer),
        )
    analytics_service.track_event(
        db,
        event=payload.event,
        session_id=payload.session_id,
        page=payload.page,
        device=ua(request)[0],
        browser=ua(request)[1],
        os=ua(request)[2],
        country=analytics_service.client_country(request),
        referrer=analytics_service.referrer_category(payload.referrer),
        upload_id=payload.upload_id,
        payload=payload.props,
    )
    return IngestResult(ok=True)


# --- helpers ----------------------------------------------------------------


def is_bot(request: Request) -> bool:
    return analytics_service.is_bot(request.headers.get("user-agent"))


def rate_allow(key: str, limit: int) -> bool:
    return get_rate_limiter().allow(key, limit=limit)


def ua(request: Request):
    return analytics_service.ua_parts(request.headers.get("user-agent"))
