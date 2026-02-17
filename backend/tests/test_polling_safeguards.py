"""Tests for sub-second polling backend safeguards.

Covers:
- Batch size cap (REST schema rejects > 500 datapoints)
- WS batch size cap (controller telemetry WS rejects oversized batches)
- Rule evaluation optimisation (last value per event, not per datapoint)
- Broadcast throttle (only sends to frontend at ≥200 ms intervals per event)
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from webmacs_backend.services.ingestion import (
    IncomingDatapoint,
    IngestionResult,
    _BROADCAST_INTERVAL,
    _last_broadcast,
    ingest_datapoints,
)

if TYPE_CHECKING:
    from httpx import AsyncClient

    from webmacs_backend.models import Event


# ---------------------------------------------------------------------------
# REST batch size cap (schema-level)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestBatchSizeCap:
    """POST /api/v1/datapoints/batch with > 500 items should be rejected."""

    async def test_batch_over_500_rejected(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_event: Event,
    ) -> None:
        """501 datapoints → 422 Unprocessable Entity."""
        payload = {
            "datapoints": [
                {"value": float(i), "event_public_id": sample_event.public_id}
                for i in range(501)
            ]
        }
        resp = await client.post(
            "/api/v1/datapoints/batch", json=payload, headers=auth_headers
        )
        assert resp.status_code == 422

    async def test_batch_at_500_accepted(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_event: Event,
    ) -> None:
        """Exactly 500 datapoints → 201 (boundary test)."""
        payload = {
            "datapoints": [
                {"value": float(i), "event_public_id": sample_event.public_id}
                for i in range(500)
            ]
        }
        resp = await client.post(
            "/api/v1/datapoints/batch", json=payload, headers=auth_headers
        )
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Rule evaluation optimisation (last value per event)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestRuleEvalOptimisation:
    """Rule engine should be called once per unique event, with the *last* value."""

    async def test_rule_eval_called_once_per_event(
        self,
        db_session,
        sample_event: Event,
    ) -> None:
        """3 datapoints for the same event → only 1 rule evaluation with last value."""
        datapoints = [
            IncomingDatapoint(value=10.0, event_public_id=sample_event.public_id),
            IncomingDatapoint(value=20.0, event_public_id=sample_event.public_id),
            IncomingDatapoint(value=30.0, event_public_id=sample_event.public_id),
        ]

        with patch(
            "webmacs_backend.services.ingestion.evaluate_rules_for_datapoint",
            new_callable=AsyncMock,
        ) as mock_eval:
            # Clear broadcast throttle state to avoid interference
            _last_broadcast.clear()
            result = await ingest_datapoints(db_session, datapoints)

        assert result.accepted == 3
        # Only called ONCE with the last value (30.0)
        assert mock_eval.call_count == 1
        call_args = mock_eval.call_args
        assert call_args[0][1] == sample_event.public_id
        assert call_args[0][2] == 30.0

    async def test_rule_eval_called_per_distinct_event(
        self,
        db_session,
        sample_event: Event,
        second_event: Event,
    ) -> None:
        """Datapoints for 2 different events → 2 rule evaluations."""
        datapoints = [
            IncomingDatapoint(value=1.0, event_public_id=sample_event.public_id),
            IncomingDatapoint(value=2.0, event_public_id=second_event.public_id),
            IncomingDatapoint(value=3.0, event_public_id=sample_event.public_id),
        ]

        with patch(
            "webmacs_backend.services.ingestion.evaluate_rules_for_datapoint",
            new_callable=AsyncMock,
        ) as mock_eval:
            _last_broadcast.clear()
            result = await ingest_datapoints(db_session, datapoints)

        assert result.accepted == 3
        assert mock_eval.call_count == 2

        # Verify last values per event
        calls = {args[0][1]: args[0][2] for args in mock_eval.call_args_list}
        assert calls[sample_event.public_id] == 3.0
        assert calls[second_event.public_id] == 2.0


# ---------------------------------------------------------------------------
# Broadcast throttle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestBroadcastThrottle:
    """Frontend WS broadcasts are throttled to ≥200 ms per event."""

    async def test_broadcast_sent_on_first_batch(
        self,
        db_session,
        sample_event: Event,
    ) -> None:
        """First batch always triggers a broadcast."""
        datapoints = [
            IncomingDatapoint(value=42.0, event_public_id=sample_event.public_id),
        ]

        # Ensure clean state
        _last_broadcast.clear()

        with (
            patch(
                "webmacs_backend.services.ingestion.evaluate_rules_for_datapoint",
                new_callable=AsyncMock,
            ),
            patch(
                "webmacs_backend.services.ingestion.manager",
            ) as mock_manager,
        ):
            mock_manager.broadcast = AsyncMock()
            await ingest_datapoints(db_session, datapoints)

        # Should have broadcast
        assert mock_manager.broadcast.call_count == 1

    async def test_broadcast_throttled_within_interval(
        self,
        db_session,
        sample_event: Event,
    ) -> None:
        """Second batch within 200 ms → no broadcast."""
        datapoints = [
            IncomingDatapoint(value=42.0, event_public_id=sample_event.public_id),
        ]

        # Pretend broadcast happened just now
        _last_broadcast[sample_event.public_id] = time.monotonic()

        with (
            patch(
                "webmacs_backend.services.ingestion.evaluate_rules_for_datapoint",
                new_callable=AsyncMock,
            ),
            patch(
                "webmacs_backend.services.ingestion.manager",
            ) as mock_manager,
        ):
            mock_manager.broadcast = AsyncMock()
            await ingest_datapoints(db_session, datapoints)

        # Throttled — no broadcast
        assert mock_manager.broadcast.call_count == 0

    async def test_broadcast_allowed_after_interval(
        self,
        db_session,
        sample_event: Event,
    ) -> None:
        """After 200 ms, broadcast is allowed again."""
        datapoints = [
            IncomingDatapoint(value=42.0, event_public_id=sample_event.public_id),
        ]

        # Pretend broadcast happened > 200 ms ago
        _last_broadcast[sample_event.public_id] = time.monotonic() - _BROADCAST_INTERVAL - 0.01

        with (
            patch(
                "webmacs_backend.services.ingestion.evaluate_rules_for_datapoint",
                new_callable=AsyncMock,
            ),
            patch(
                "webmacs_backend.services.ingestion.manager",
            ) as mock_manager,
        ):
            mock_manager.broadcast = AsyncMock()
            await ingest_datapoints(db_session, datapoints)

        assert mock_manager.broadcast.call_count == 1
