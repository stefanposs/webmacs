"""Tests for datapoint endpoints — the hottest path in the system.

The controller pushes batch datapoints every poll_interval (100 ms in prod),
and the frontend polls /latest every second. These two endpoints MUST work.

Covers:
- POST /datapoints/batch  → bulk insert (happy path + empty batch)
- GET  /datapoints/latest → one row per event, most recent value
- GET  /datapoints/{id}   → single datapoint retrieval
- Auth guard              → all endpoints require a token
"""

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient

    from webmacs_backend.models import Event

# ---------------------------------------------------------------------------
# Batch create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestBatchCreate:
    """POST /api/v1/datapoints/batch"""

    async def test_batch_create_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_event: Event,
    ) -> None:
        """Inserting multiple datapoints returns 201 with count."""
        payload = {
            "datapoints": [
                {"value": 21.5, "event_public_id": sample_event.public_id},
                {"value": 22.0, "event_public_id": sample_event.public_id},
                {"value": 22.3, "event_public_id": sample_event.public_id},
            ]
        }
        resp = await client.post(
            "/api/v1/datapoints/batch", json=payload, headers=auth_headers
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "success"
        assert "3" in body["message"]  # "3 datapoints successfully created."

    async def test_batch_create_empty_list(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Empty batch should still succeed (0 datapoints)."""
        resp = await client.post(
            "/api/v1/datapoints/batch",
            json={"datapoints": []},
            headers=auth_headers,
        )
        # Depending on validation: either 201 with "0 datapoints" or 422.
        # Current implementation accepts empty list → 201.
        assert resp.status_code in (201, 422)

    async def test_batch_create_unauthenticated(self, client: AsyncClient) -> None:
        """No token → 401."""
        resp = await client.post(
            "/api/v1/datapoints/batch",
            json={"datapoints": [{"value": 1.0, "event_public_id": "x"}]},
        )
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Latest datapoints (one per event)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestLatestDatapoints:
    """GET /api/v1/datapoints/latest"""

    async def test_latest_returns_one_per_event(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_event: Event,
        second_event: Event,
    ) -> None:
        """After inserting datapoints for 2 events, /latest returns 2 rows."""
        # Insert 2 datapoints for event 1 (only the last should appear)
        await client.post(
            "/api/v1/datapoints/batch",
            json={
                "datapoints": [
                    {"value": 10.0, "event_public_id": sample_event.public_id},
                    {"value": 20.0, "event_public_id": sample_event.public_id},
                ]
            },
            headers=auth_headers,
        )
        # Insert 1 datapoint for event 2
        await client.post(
            "/api/v1/datapoints/batch",
            json={
                "datapoints": [
                    {"value": 5.0, "event_public_id": second_event.public_id},
                ]
            },
            headers=auth_headers,
        )

        resp = await client.get("/api/v1/datapoints/latest", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()

        # Should have exactly 2 entries (one per event)
        assert len(body) == 2

        # Extract by event id for deterministic assertion
        by_event = {dp["event_public_id"]: dp for dp in body}
        assert by_event[sample_event.public_id]["value"] == 20.0
        assert by_event[second_event.public_id]["value"] == 5.0

    async def test_latest_empty_when_no_datapoints(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """No datapoints in DB → empty list."""
        resp = await client.get("/api/v1/datapoints/latest", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_latest_unauthenticated(self, client: AsyncClient) -> None:
        """No token → 401."""
        resp = await client.get("/api/v1/datapoints/latest")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Single datapoint CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestSingleDatapoint:
    """POST /datapoints + GET /datapoints/{id}"""

    async def test_create_and_get_single(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_event: Event,
    ) -> None:
        """Create one datapoint, then retrieve it by public_id."""
        # Create
        create_resp = await client.post(
            "/api/v1/datapoints",
            json={"value": 42.0, "event_public_id": sample_event.public_id},
            headers=auth_headers,
        )
        assert create_resp.status_code == 201

        # List to find the public_id (paginated response)
        list_resp = await client.get("/api/v1/datapoints", headers=auth_headers)
        assert list_resp.status_code == 200
        dp_list = list_resp.json()["data"]
        assert len(dp_list) == 1

        public_id = dp_list[0]["public_id"]

        # Get by id
        get_resp = await client.get(
            f"/api/v1/datapoints/{public_id}", headers=auth_headers
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["value"] == 42.0

    async def test_get_nonexistent_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Unknown public_id → 404."""
        resp = await client.get(
            "/api/v1/datapoints/does-not-exist", headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_create_with_unknown_event_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Datapoint referencing a non-existent event → 404."""
        resp = await client.post(
            "/api/v1/datapoints",
            json={"value": 1.0, "event_public_id": "no-such-event"},
            headers=auth_headers,
        )
        assert resp.status_code == 404
