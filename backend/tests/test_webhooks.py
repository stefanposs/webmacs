"""Tests for Webhook CRUD API and Dispatcher."""


import pytest

pytestmark = pytest.mark.anyio


# ─── CRUD Tests ──────────────────────────────────────────────────────────────


async def test_create_webhook(client, auth_headers, admin_user):
    """POST /api/v1/webhooks creates a webhook subscription."""
    response = await client.post(
        "/api/v1/webhooks",
        json={
            "url": "https://hooks.example.com/test",
            "secret": "my-secret",
            "events": ["sensor.threshold_exceeded"],
            "enabled": True,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert "Webhook" in data["message"]


async def test_create_webhook_rejects_invalid_url(client, auth_headers, admin_user):
    """POST /api/v1/webhooks rejects non-HTTP URLs."""
    response = await client.post(
        "/api/v1/webhooks",
        json={
            "url": "ftp://example.com",
            "events": ["sensor.threshold_exceeded"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_create_webhook_rejects_empty_events(client, auth_headers, admin_user):
    """POST /api/v1/webhooks rejects empty events list."""
    response = await client.post(
        "/api/v1/webhooks",
        json={
            "url": "https://example.com/hook",
            "events": [],
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_create_webhook_duplicate_url(client, auth_headers, admin_user, sample_webhook):
    """POST /api/v1/webhooks rejects duplicate URL."""
    response = await client.post(
        "/api/v1/webhooks",
        json={
            "url": "https://example.com/hook",
            "events": ["sensor.threshold_exceeded"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 409


async def test_list_webhooks(client, auth_headers, admin_user, sample_webhook):
    """GET /api/v1/webhooks returns paginated list."""
    response = await client.get("/api/v1/webhooks", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert data["data"][0]["public_id"] == "wh-test-001"
    assert data["data"][0]["url"] == "https://example.com/hook"
    assert "sensor.threshold_exceeded" in data["data"][0]["events"]


async def test_get_webhook(client, auth_headers, admin_user, sample_webhook):
    """GET /api/v1/webhooks/{id} returns a single webhook."""
    response = await client.get("/api/v1/webhooks/wh-test-001", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "https://example.com/hook"
    assert data["enabled"] is True


async def test_get_webhook_not_found(client, auth_headers, admin_user):
    """GET /api/v1/webhooks/{id} returns 404 for missing webhook."""
    response = await client.get("/api/v1/webhooks/nonexistent", headers=auth_headers)
    assert response.status_code == 404


async def test_update_webhook(client, auth_headers, admin_user, sample_webhook):
    """PUT /api/v1/webhooks/{id} updates enabled status."""
    response = await client.put(
        "/api/v1/webhooks/wh-test-001",
        json={"enabled": False},
        headers=auth_headers,
    )
    assert response.status_code == 200

    # Verify update
    get_response = await client.get("/api/v1/webhooks/wh-test-001", headers=auth_headers)
    assert get_response.json()["enabled"] is False


async def test_delete_webhook(client, auth_headers, admin_user, sample_webhook):
    """DELETE /api/v1/webhooks/{id} removes webhook."""
    response = await client.delete("/api/v1/webhooks/wh-test-001", headers=auth_headers)
    assert response.status_code == 200

    # Verify deletion
    get_response = await client.get("/api/v1/webhooks/wh-test-001", headers=auth_headers)
    assert get_response.status_code == 404


async def test_webhooks_require_admin(client, db_session):
    """Webhook endpoints require admin authentication."""
    response = await client.get("/api/v1/webhooks")
    assert response.status_code in (401, 403)


# ─── Dispatcher Tests ────────────────────────────────────────────────────────


async def test_build_payload():
    """build_payload creates correct structure."""
    from webmacs_backend.enums import WebhookEventType
    from webmacs_backend.services import build_payload

    payload = build_payload(
        WebhookEventType.sensor_threshold_exceeded,
        device="revpi-01",
        sensor="temp_01",
        value=85.2,
    )
    assert payload["type"] == "sensor.threshold_exceeded"
    assert payload["device"] == "revpi-01"
    assert payload["sensor"] == "temp_01"
    assert payload["value"] == 85.2
    assert "time" in payload


async def test_sign_payload():
    """HMAC-SHA256 signature includes timestamp for replay protection."""
    from webmacs_backend.services import _sign_payload

    sig1 = _sign_payload('{"test": 1}', "secret", "1707600000")
    sig2 = _sign_payload('{"test": 1}', "secret", "1707600000")
    assert sig1 == sig2
    assert len(sig1) == 64  # hex digest


async def test_sign_payload_different_secrets():
    """Different secrets produce different signatures."""
    from webmacs_backend.services import _sign_payload

    sig1 = _sign_payload('{"test": 1}', "secret1", "1707600000")
    sig2 = _sign_payload('{"test": 1}', "secret2", "1707600000")
    assert sig1 != sig2


async def test_sign_payload_different_timestamps():
    """Different timestamps produce different signatures (replay protection)."""
    from webmacs_backend.services import _sign_payload

    sig1 = _sign_payload('{"test": 1}', "secret", "1707600000")
    sig2 = _sign_payload('{"test": 1}', "secret", "1707600001")
    assert sig1 != sig2
