from __future__ import annotations

import datetime as dt
import json
import uuid

from sqlalchemy import select

from app.models.ad_event import AdEvent
from app.models.analytics import Analytics
from app.models.audit_log import AuditLog
from app.models.enums import UserRole
from app.models.traffic_stat import TrafficStat

BOT_UA = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def _enable_ads(client, auth_headers, create_user):
    create_user("adadmin@example.com", role=UserRole.ADMIN)
    headers = auth_headers("adadmin@example.com")
    client.put(
        "/api/v1/admin/settings",
        headers=headers,
        json=[{"key": "ads.enabled", "value": True}],
    )
    return headers


def _make_provider(client, headers, **overrides):
    payload = {
        "name": "TestProvider",
        "provider_type": "script",
        "zone_id": "12345",
        "enabled": True,
        **overrides,
    }
    resp = client.post("/api/v1/admin/ads/providers", headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _make_placement(client, headers, provider_id, name="test_slot"):
    resp = client.post(
        "/api/v1/admin/ads/placements",
        headers=headers,
        json={
            "name": name,
            "label": "Landing top",
            "enabled": True,
            "responsive": True,
            "slots": [{"provider_id": provider_id, "priority": 1}],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# --- public ad configuration -------------------------------------------------


def test_public_ad_config_off_by_default(client):
    body = client.get("/api/v1/ads/config").json()
    assert body["enabled"] is False
    assert body["placements"] == {}


def test_enabled_config_serves_safe_slot(client, auth_headers, create_user):
    headers = _enable_ads(client, auth_headers, create_user)
    provider = _make_provider(client, headers, api_key="super-secret-key-abc")
    _make_placement(client, headers, provider["id"])

    body = client.get("/api/v1/ads/config").json()
    assert body["enabled"] is True
    placement = body["placements"].get("test_slot")
    assert placement is not None
    assert placement["behavior"] == "lazy"
    assert len(placement["slots"]) == 1
    slot = placement["slots"][0]
    assert slot["provider_id"] == provider["id"]
    assert slot["name"] == "TestProvider"
    assert slot["render"]["kind"] == "script"
    assert "invoke.js" in slot["render"]["content"]

    serialized = json.dumps(body)
    assert "super-secret-key-abc" not in serialized
    assert "api_key" not in serialized


def test_disabled_provider_not_served(client, auth_headers, create_user):
    headers = _enable_ads(client, auth_headers, create_user)
    provider = _make_provider(client, headers, enabled=False)
    _make_placement(client, headers, provider["id"])
    body = client.get("/api/v1/ads/config").json()
    assert "test_slot" not in body["placements"]


def test_custom_script_served_isolated_kind(client, auth_headers, create_user):
    headers = _enable_ads(client, auth_headers, create_user)
    provider = _make_provider(
        client,
        headers,
        name="CustomScript",
        provider_type="custom",
        custom_script="<script>console.log('x')</script>",
    )
    _make_placement(client, headers, provider["id"])
    body = client.get("/api/v1/ads/config").json()
    slot = body["placements"]["test_slot"]["slots"][0]
    assert slot["type"] == "custom"
    assert "console.log" in slot["render"]["content"]


# --- analytics ingestion -----------------------------------------------------


def _post_event(client, event, session="sess-1", page="/", ua=CHROME_UA, referrer=None):
    return client.post(
        "/api/v1/analytics/events",
        headers={"User-Agent": ua},
        json={
            "event": event,
            "session_id": session,
            "page": page,
            "referrer": referrer,
        },
    )


def test_page_view_tracked(client, db):
    resp = _post_event(client, "page_view")
    assert resp.status_code == 200
    assert db.scalar(
        db.query(TrafficStat).filter(TrafficStat.page_views > 0).exists().select()
    ) is True
    row = db.query(TrafficStat).first()
    assert row.page_views == 1
    assert row.page_url == "/"
    assert row.browser == "Chrome"
    assert row.device == "desktop"
    assert row.os == "Windows"
    assert db.query(Analytics).filter(Analytics.event_type == "page_view").count() == 1


def test_session_counted_once_per_day(client, db):
    _post_event(client, "page_view")
    _post_event(client, "page_view")
    assert db.query(TrafficStat).first().sessions == 1


def test_bot_events_dropped(client, db):
    resp = _post_event(client, "page_view", ua=BOT_UA)
    assert resp.status_code == 200
    assert db.query(TrafficStat).count() == 0
    assert db.query(Analytics).count() == 0


def test_unknown_event_dropped(client, db):
    resp = _post_event(client, "totally_bogus_event")
    assert resp.status_code == 200
    assert db.query(Analytics).count() == 0


def test_funnel_events_increment_counters(client, db):
    for event in [
        "upload_started",
        "upload_completed",
        "processing_completed",
        "get_hd_clicked",
        "whatsapp_opened",
        "media_delivered",
        "upload_failed",
    ]:
        _post_event(client, event)
    row = db.query(TrafficStat).first()
    assert row.uploads == 1
    assert row.uploads_completed == 1
    assert row.processing_completed == 1
    assert row.get_hd_clicks == 1
    assert row.whatsapp_opens == 1
    assert row.media_deliveries == 1
    assert row.errors == 1


def test_ad_event_tracked(client, db, auth_headers, create_user):
    headers = _enable_ads(client, auth_headers, create_user)
    provider = _make_provider(client, headers)
    resp = client.post(
        "/api/v1/ads/event",
        headers={"User-Agent": CHROME_UA},
        json={
            "event_type": "impression",
            "placement": "test_slot",
            "page": "/",
            "session_id": "sess-x",
            "provider_id": provider["id"],
        },
    )
    assert resp.status_code == 200
    ad_event = db.query(AdEvent).first()
    assert ad_event is not None
    assert ad_event.event_type == "impression"
    assert ad_event.provider_name == "TestProvider"
    stat = db.query(TrafficStat).first()
    assert stat.ad_impressions == 1


# --- admin ads endpoints -----------------------------------------------------


def test_ads_admin_gated(client, auth_headers, create_user):
    create_user("viewer@example.com", role=UserRole.VIEWER)
    headers = auth_headers("viewer@example.com")
    assert client.get("/api/v1/admin/ads/providers", headers=headers).status_code == 200
    assert (
        client.post("/api/v1/admin/ads/providers", headers=headers, json={}).status_code
        == 403
    )


def test_ads_admin_provider_crud(client, auth_headers, create_user):
    headers = _enable_ads(client, auth_headers, create_user)
    provider = _make_provider(client, headers)
    pid = provider["id"]
    assert pid
    listed = client.get("/api/v1/admin/ads/providers", headers=headers).json()
    assert any(p["id"] == pid for p in listed)

    updated = client.put(
        f"/api/v1/admin/ads/providers/{pid}",
        headers=headers,
        json={"publisher_id": "ca-pub-1", "enabled": True},
    ).json()
    assert updated["publisher_id"] == "ca-pub-1"

    tested = client.post(
        f"/api/v1/admin/ads/providers/{pid}/test", headers=headers
    ).json()
    assert tested["ok"] is True

    assert (
        client.delete(f"/api/v1/admin/ads/providers/{pid}", headers=headers).status_code
        == 204
    )
    assert (
        client.get(f"/api/v1/admin/ads/providers/{pid}", headers=headers).status_code
        == 404
    )


def test_ads_admin_placement_slots_reorder_preview(client, auth_headers, create_user):
    headers = _enable_ads(client, auth_headers, create_user)
    p1 = _make_provider(client, headers, name="ProviderA")
    p2 = _make_provider(client, headers, name="ProviderB", zone_id="98765")
    placement = _make_placement(client, headers, p1["id"])
    pid = placement["id"]
    assert len(placement["slots"]) == 1

    updated = client.put(
        f"/api/v1/admin/ads/placements/{pid}/slots",
        headers=headers,
        json=[
            {"provider_id": p2["id"], "priority": 1},
            {"provider_id": p1["id"], "priority": 2},
        ],
    ).json()
    assert [s["provider_name"] for s in updated["slots"]] == ["ProviderB", "ProviderA"]

    reordered = client.put(
        f"/api/v1/admin/ads/placements/{pid}/reorder",
        headers=headers,
        json={"provider_ids": [p1["id"], p2["id"]]},
    ).json()
    assert [s["provider_name"] for s in reordered["slots"]] == ["ProviderA", "ProviderB"]

    preview = client.get(
        f"/api/v1/admin/ads/placements/{pid}/preview", headers=headers
    ).json()
    assert preview["enabled"] is True
    assert preview["placement"]["slots"][0]["name"] == "ProviderA"

    assert (
        client.delete(f"/api/v1/admin/ads/placements/{pid}", headers=headers).status_code
        == 204
    )


def test_ads_overview_and_analytics(client, auth_headers, create_user, db):
    headers = _enable_ads(client, auth_headers, create_user)
    provider = _make_provider(client, headers)
    _make_placement(client, headers, provider["id"])
    client.post(
        "/api/v1/ads/event",
        headers={"User-Agent": CHROME_UA},
        json={"event_type": "impression", "placement": "test_slot", "page": "/"},
    )

    overview = client.get("/api/v1/admin/ads/overview", headers=headers).json()
    assert overview["enabled"] is True
    assert overview["providers_total"] >= 1
    assert overview["placements_total"] >= 1
    assert overview["impressions"] >= 1

    analytics = client.get(
        "/api/v1/admin/ads/analytics?days=30&group=provider", headers=headers
    ).json()
    assert analytics["totals"]["impressions"] >= 1
    assert any(item["impression"] >= 1 for item in analytics["items"])


def test_audit_log_created_on_ad_mutations(client, auth_headers, create_user, db):
    headers = _enable_ads(client, auth_headers, create_user)
    provider = _make_provider(client, headers)
    audit = db.scalar(
        select(AuditLog).where(AuditLog.action == "admin.ad_provider_created")
    )
    assert audit is not None
    assert audit.resource_id == provider["id"]


# --- admin analytics endpoints -----------------------------------------------


def test_analytics_admin_overview_and_timeseries(client, auth_headers, create_user):
    create_user("stats@example.com", role=UserRole.ADMIN)
    headers = auth_headers("stats@example.com")
    _post_event(client, "page_view")
    _post_event(client, "get_hd_clicked")
    _post_event(client, "media_delivered")

    overview = client.get(
        "/api/v1/admin/analytics/overview?days=30", headers=headers
    ).json()
    assert overview["visitors"] >= 1
    assert overview["page_views"] >= 1
    assert overview["get_hd_clicks"] >= 1
    assert overview["media_deliveries"] >= 1

    series = client.get(
        "/api/v1/admin/analytics/timeseries?days=30", headers=headers
    ).json()
    assert series["points"], "expected at least one daily point"
    assert series["points"][0]["page_views"] >= 1

    pages = client.get("/api/v1/admin/analytics/top-pages", headers=headers).json()
    assert any(item["key"] == "/" for item in pages["items"])

    devices = client.get(
        "/api/v1/admin/analytics/devices?dimension=browser", headers=headers
    ).json()
    assert any(item["key"] == "Chrome" for item in devices["items"])

    referrers = client.get("/api/v1/admin/analytics/referrers", headers=headers).json()
    assert any(item["key"] == "direct" for item in referrers["items"])


def test_analytics_admin_events_filter(client, auth_headers, create_user):
    create_user("stats@example.com", role=UserRole.ADMIN)
    headers = auth_headers("stats@example.com")
    _post_event(client, "page_view")
    page = client.get(
        "/api/v1/admin/analytics/events?event=page_view", headers=headers
    ).json()
    assert page["total"] == 1
    assert page["items"][0]["event_type"] == "page_view"


def test_analytics_retention_purges_old_rows(client, auth_headers, create_user, db):
    create_user("stats@example.com", role=UserRole.ADMIN)
    headers = auth_headers("stats@example.com")
    _post_event(client, "page_view")
    old = Analytics(
        event_type="page_view",
        session_id="old-session",
        page="/",
        created_at=dt.datetime(2020, 1, 1),
    )
    db.add(old)
    db.commit()

    result = client.post("/api/v1/admin/analytics/retention/run", headers=headers).json()
    assert result["analytics_events_deleted"] >= 1
    assert db.query(Analytics).filter(Analytics.session_id == "old-session").count() == 0
