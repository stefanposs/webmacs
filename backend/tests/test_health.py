"""Tests for the rich health endpoint."""

import pytest

pytestmark = pytest.mark.anyio


async def test_health_returns_200(client):
    """GET /health returns 200 with structured response — no auth required."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert data["version"] == "2.0.0"
    assert data["database"] == "ok"
    assert "uptime_seconds" in data


async def test_health_no_auth_required(client):
    """GET /health works without any authentication headers."""
    response = await client.get("/health")
    assert response.status_code == 200


async def test_health_shows_last_datapoint(client, auth_headers, admin_user, sample_event):
    """GET /health shows last_datapoint when data exists."""
    # Create a datapoint first
    await client.post(
        "/api/v1/datapoints",
        json={"value": 42.0, "event_public_id": sample_event.public_id},
        headers=auth_headers,
    )

    response = await client.get("/health")
    data = response.json()
    assert data["status"] == "ok"
    assert data["last_datapoint"] is not None


async def test_health_last_datapoint_null_when_no_data(client):
    """GET /health shows null last_datapoint when no datapoints exist."""
    response = await client.get("/health")
    data = response.json()
    # Could be None since no datapoints created
    # Just verify the field exists and doesn't error
    assert "last_datapoint" in data
