"""Tests for event endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestEvents:
    """Event CRUD tests."""

    async def test_create_event(self, client: AsyncClient, auth_headers: dict) -> None:
        response = await client.post(
            "/api/v1/events/",
            json={"name": "temp1", "min_value": 0.0, "max_value": 100.0, "unit": "°C", "type": "sensor"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["status"] == "success"

    async def test_list_events(self, client: AsyncClient, auth_headers: dict) -> None:
        # Create first
        await client.post(
            "/api/v1/events/",
            json={"name": "pressure1", "min_value": 0.0, "max_value": 10.0, "unit": "bar", "type": "sensor"},
            headers=auth_headers,
        )
        response = await client.get("/api/v1/events/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["total"] >= 1

    async def test_create_duplicate_event(self, client: AsyncClient, auth_headers: dict) -> None:
        payload = {"name": "unique_sensor", "min_value": 0.0, "max_value": 50.0, "unit": "mV", "type": "sensor"}
        await client.post("/api/v1/events/", json=payload, headers=auth_headers)
        response = await client.post("/api/v1/events/", json=payload, headers=auth_headers)
        assert response.status_code == 409

    async def test_unauthorized_access(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/events/")
        assert response.status_code == 401
