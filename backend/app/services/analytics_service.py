from __future__ import annotations

"""Privacy-conscious traffic analytics.

Event ingestion is deliberately lightweight:

* anonymous client-generated session ids (no accounts, no cookies required)
* no raw IP addresses are stored — only coarse category labels
* country is only recorded when a trusted proxy header provides it
* obvious crawler/bot traffic is dropped
* raw events are purged after a configurable retention; the daily aggregate
  table keeps the reporting cube indefinitely
"""

import datetime as dt
import hashlib
import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.analytics import Analytics
from app.models.enums import AnalyticsEventName
from app.models.traffic_stat import TrafficStat
from app.services.ads.service import analytics_enabled

_BOT_PATTERNS = re.compile(
    r"bot|crawler|spider|scraper|slurp|curl|wget|python-requests|"
    r"go-http-client|java/|node-fetch|httpie|postman|headless|"
    r"facebookexternalhit|twitterbot|linkedinbot|whatsapp|telegrambot|"
    r"preview|uptimerobot|pingdom|monitor|semrush|ahrefs|mj12bot|"
    r"yandexbot|bingbot|googlebot|baiduspider|duckduckbot|petalbot",
    re.IGNORECASE,
)

_VALID_EVENTS = frozenset(e.value for e in AnalyticsEventName)

_EVENT_COUNTER: dict[str, str] = {
    "page_view": "page_views",
    "upload_started": "uploads",
    "upload_completed": "uploads_completed",
    "upload_failed": "errors",
    "processing_started": "uploads",
    "processing_completed": "processing_completed",
    "processing_failed": "errors",
    "get_hd_clicked": "get_hd_clicks",
    "whatsapp_opened": "whatsapp_opens",
    "whatsapp_request": "whatsapp_requests",
    "whatsapp_message_received": "whatsapp_requests",
    "media_delivered": "media_deliveries",
}

_REFERRER_CATEGORIES: dict[str, tuple[re.Pattern, ...]] = {
    "search": (
        re.compile(r"google\.|bing\.|yahoo\.|duckduckgo\.|baidu\.|yandex\.", re.I),
    ),
    "social": (
        re.compile(r"facebook\.|instagram\.|t\.me|whatsapp\.|twitter\.|x\.com|"
                   r"linkedin\.|pinterest\.|reddit\.|tiktok\.|youtube\.", re.I),
    ),
}


def ua_parts(user_agent: str | None) -> tuple[str, str, str]:
    """Coarse device / browser / OS categories from a user agent string."""
    ua = user_agent or ""
    low = ua.lower()
    if "mobile" in low or "android" in low or "iphone" in low:
        device = "mobile"
    elif "tablet" in low or "ipad" in low:
        device = "tablet"
    else:
        device = "desktop"
    if "edg/" in low:
        browser = "Edge"
    elif "opr/" in low or "opera" in low:
        browser = "Opera"
    elif "chrome" in low and "chromium" not in low:
        browser = "Chrome"
    elif "firefox" in low:
        browser = "Firefox"
    elif "safari" in low:
        browser = "Safari"
    else:
        browser = "Other"
    if "windows" in low:
        os = "Windows"
    elif "android" in low:
        os = "Android"
    elif "iphone" in low or "ios" in low:
        os = "iOS"
    elif "mac os" in low:
        os = "macOS"
    elif "linux" in low:
        os = "Linux"
    else:
        os = "Other"
    return device, browser, os


def is_bot(user_agent: str | None) -> bool:
    return bool(user_agent and _BOT_PATTERNS.search(user_agent))


def referrer_category(referrer: str | None) -> str:
    if not referrer:
        return "direct"
    low = referrer.lower()
    for category, patterns in _REFERRER_CATEGORIES.items():
        if any(p.search(low) for p in patterns):
            return category
    return "other"


def client_ip_hash(request) -> str:
    """Non-reversible key for rate limiting; never persisted."""
    host = request.client.host if request.client else "unknown"
    return hashlib.sha256(host.encode("utf-8")).hexdigest()[:24]


def client_country(request) -> str | None:
    """Country code from a trusted edge header only (e.g. cf-ipcountry)."""
    code = request.headers.get("cf-ipcountry") or request.headers.get("x-country-code")
    if not code:
        return None
    code = code.strip().upper()
    return code if code.isalpha() and len(code) == 2 else None


def is_valid_event(event: str) -> bool:
    return event in _VALID_EVENTS


def _page_path(page: str | None) -> str:
    if not page:
        return "/"
    page = page[:128]
    return page if page.startswith("/") else f"/{page}"


def track_event(
    db: Session,
    *,
    event: str,
    session_id: str | None = None,
    page: str | None = None,
    device: str = "unknown",
    browser: str = "unknown",
    os: str = "unknown",
    country: str | None = None,
    referrer: str | None = None,
    upload_id: uuid.UUID | None = None,
    payload: dict | None = None,
    commit: bool = True,
) -> None:
    """Record a single analytics event (best-effort, never raises)."""
    try:
        if not analytics_enabled(db):
            return
        if not is_valid_event(event):
            return
        referrer = referrer or "direct"
        stat_date = dt.date.today()
        row = _get_or_create_daily(
            db,
            stat_date=stat_date,
            page=_page_path(page),
            device=device or "unknown",
            browser=browser or "unknown",
            os=os or "unknown",
            country=country or "unknown",
            referrer=referrer,
        )
        row.events_count += 1
        counter = _EVENT_COUNTER.get(event)
        if counter is not None:
            setattr(row, counter, getattr(row, counter) + 1)
        if event == "page_view":
            db.add(
                Analytics(
                    event_type=event,
                    upload_id=upload_id,
                    session_id=session_id,
                    page=_page_path(page),
                    device=device or "unknown",
                    browser=browser or "unknown",
                    os=os or "unknown",
                    country=country or "unknown",
                    referrer_category=referrer,
                    payload=payload or {},
                )
            )
        if commit:
            db.commit()
    except Exception:
        db.rollback()


def track_ad_event(
    db: Session,
    *,
    placement: str,
    page: str | None,
    device: str = "unknown",
    browser: str = "unknown",
    os: str = "unknown",
    country: str | None = None,
    event: str = "impression",
) -> None:
    """Roll an ad event into the daily aggregate (best-effort)."""
    try:
        if not analytics_enabled(db):
            return
        row = _get_or_create_daily(
            db,
            stat_date=dt.date.today(),
            page=_page_path(page),
            device=device or "unknown",
            browser=browser or "unknown",
            os=os or "unknown",
            country=country or "unknown",
            referrer="direct",
        )
        row.events_count += 1
        if event == "click":
            row.ad_clicks += 1
        elif event == "load_failure":
            row.ad_load_failures += 1
        else:
            row.ad_impressions += 1
        db.commit()
    except Exception:
        db.rollback()


def _get_or_create_daily(
    db: Session,
    *,
    stat_date: dt.date,
    page: str,
    device: str,
    browser: str,
    os: str,
    country: str,
    referrer: str,
) -> TrafficStat:
    row = db.scalar(
        select(TrafficStat).where(
            TrafficStat.stat_date == stat_date,
            TrafficStat.page_url == page,
            TrafficStat.device == device,
            TrafficStat.browser == browser,
            TrafficStat.os == os,
            TrafficStat.country == country,
            TrafficStat.referrer == referrer,
        )
    )
    if row is None:
        row = TrafficStat(
            stat_date=stat_date,
            page_url=page,
            device=device,
            browser=browser,
            os=os,
            country=country,
            referrer=referrer,
        )
        db.add(row)
        db.flush()
    return row


def session_seen_today(db: Session, session_id: str | None) -> bool:
    """True when this anonymous session already produced events today."""
    if not session_id:
        return True
    today_start = dt.datetime.combine(dt.date.today(), dt.time.min).replace(tzinfo=None)
    count = (
        db.scalar(
            select(func.count())
            .select_from(Analytics)
            .where(
                Analytics.session_id == session_id,
                Analytics.created_at >= today_start,
            )
        )
        or 0
    )
    return count > 0


def upsert_session(
    db: Session,
    *,
    session_id: str,
    page: str | None = None,
    device: str = "unknown",
    browser: str = "unknown",
    os: str = "unknown",
    country: str | None = None,
    referrer: str | None = None,
) -> None:
    """Count a new anonymous session for the day (best-effort, deduped)."""
    try:
        if not analytics_enabled(db) or not session_id:
            return
        if session_seen_today(db, session_id):
            return
        row = _get_or_create_daily(
            db,
            stat_date=dt.date.today(),
            page=_page_path(page),
            device=device or "unknown",
            browser=browser or "unknown",
            os=os or "unknown",
            country=country or "unknown",
            referrer=referrer or "direct",
        )
        row.sessions += 1
        db.commit()
    except Exception:
        db.rollback()


def run_retention(db: Session, days: int | None = None) -> dict:
    """Purge raw analytics + ad event rows older than the retention window."""
    from app.models.ad_event import AdEvent

    days = days or 90
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    analytics_deleted = (
        db.scalar(
            select(func.count())
            .select_from(Analytics)
            .where(Analytics.created_at < cutoff.replace(tzinfo=None))
        )
        or 0
    )
    ad_deleted = (
        db.scalar(
            select(func.count())
            .select_from(AdEvent)
            .where(AdEvent.created_at < cutoff.replace(tzinfo=None))
        )
        or 0
    )
    db.query(Analytics).filter(Analytics.created_at < cutoff.replace(tzinfo=None)).delete(
        synchronize_session=False
    )
    db.query(AdEvent).filter(AdEvent.created_at < cutoff.replace(tzinfo=None)).delete(
        synchronize_session=False
    )
    db.commit()
    return {"analytics_events_deleted": analytics_deleted, "ad_events_deleted": ad_deleted}
