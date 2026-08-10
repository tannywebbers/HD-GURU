from __future__ import annotations


def test_health_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["version"]
    assert body["environment"]
    assert body["uptime_seconds"] >= 0
    for component in ("application", "database", "redis", "workers", "storage"):
        assert component in body
        assert body[component]["status"] in {"ok", "unavailable"}
    assert body["timestamp"]


def test_ready_ok(client):
    response = client.get("/api/v1/ready")
    # In the test environment Redis may be unavailable -> 503 is acceptable.
    assert response.status_code in {200, 503}
    body = response.json()
    assert "ready" in body
    assert "checks" in body
    for component in ("database", "redis", "workers", "storage"):
        assert component in body["checks"]


def test_health_root_not_exposed(client):
    response = client.get("/health")
    assert response.status_code == 404


def test_health_root_not_exposed_ready(client):
    response = client.get("/ready")
    assert response.status_code == 404
