"""Tests for webhook dispatch safeguards (throttle + concurrency limit).

These tests verify that high-frequency sensor data cannot overwhelm the
system by flooding external webhook receivers.  Two layers of protection:

1. **Ingestion throttle** – ``_fire_webhook`` skips dispatches if the last
   one for the same sensor was less than ``_SENSOR_WEBHOOK_INTERVAL`` ago.
2. **Concurrency semaphore** – ``_dispatch_to_webhook`` limits the number
   of simultaneous outgoing HTTP requests to ``MAX_CONCURRENT_DELIVERIES``.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.anyio


# ─── Throttle tests ─────────────────────────────────────────────────────────


class TestSensorWebhookThrottle:
    """Verify that _fire_webhook throttles high-frequency dispatches."""

    def setup_method(self) -> None:
        """Reset module-level throttle state before every test."""
        from webmacs_backend.services import ingestion

        ingestion._last_sensor_dispatch.clear()

    async def test_first_call_always_dispatches(self) -> None:
        """The very first call for a sensor always creates a task."""
        from webmacs_backend.services import ingestion

        with patch.object(ingestion, "dispatch_event", new_callable=AsyncMock) as mock_dispatch:
            with patch.object(ingestion, "build_payload", return_value={"type": "sensor.reading"}):
                ingestion._fire_webhook("sensor-a", 42.0)
                # Task was created → dispatch_event was scheduled
                # Wait briefly for the fire-and-forget task
                await asyncio.sleep(0.05)
                mock_dispatch.assert_called_once()

    async def test_rapid_calls_are_throttled(self) -> None:
        """Calls within _SENSOR_WEBHOOK_INTERVAL are silently dropped."""
        from webmacs_backend.services import ingestion

        with patch.object(ingestion, "dispatch_event", new_callable=AsyncMock) as mock_dispatch:
            with patch.object(ingestion, "build_payload", return_value={"type": "sensor.reading"}):
                # First call → dispatched
                ingestion._fire_webhook("sensor-a", 1.0)
                await asyncio.sleep(0.05)
                assert mock_dispatch.call_count == 1

                # Rapid subsequent calls → throttled
                for _ in range(50):
                    ingestion._fire_webhook("sensor-a", 2.0)

                await asyncio.sleep(0.05)
                # Still only 1 call — all 50 were throttled
                assert mock_dispatch.call_count == 1

    async def test_different_sensors_are_independent(self) -> None:
        """Each sensor channel has its own throttle window."""
        from webmacs_backend.services import ingestion

        with patch.object(ingestion, "dispatch_event", new_callable=AsyncMock) as mock_dispatch:
            with patch.object(ingestion, "build_payload", return_value={"type": "sensor.reading"}):
                ingestion._fire_webhook("sensor-a", 1.0)
                ingestion._fire_webhook("sensor-b", 2.0)
                ingestion._fire_webhook("sensor-c", 3.0)
                await asyncio.sleep(0.05)
                # Each sensor gets one dispatch
                assert mock_dispatch.call_count == 3

    async def test_dispatch_resumes_after_interval(self) -> None:
        """After the throttle interval, the next call dispatches again."""
        from webmacs_backend.services import ingestion

        # Temporarily set a very short interval for testing
        original_interval = ingestion._SENSOR_WEBHOOK_INTERVAL
        ingestion._SENSOR_WEBHOOK_INTERVAL = 0.1  # 100ms

        try:
            with patch.object(ingestion, "dispatch_event", new_callable=AsyncMock) as mock_dispatch:
                with patch.object(ingestion, "build_payload", return_value={"type": "sensor.reading"}):
                    ingestion._fire_webhook("sensor-a", 1.0)
                    await asyncio.sleep(0.05)
                    assert mock_dispatch.call_count == 1

                    # Wait for throttle to expire
                    await asyncio.sleep(0.15)

                    ingestion._fire_webhook("sensor-a", 2.0)
                    await asyncio.sleep(0.05)
                    assert mock_dispatch.call_count == 2
        finally:
            ingestion._SENSOR_WEBHOOK_INTERVAL = original_interval

    async def test_throttle_prevents_task_explosion(self) -> None:
        """Simulates rapid ingestion of 500 datapoints — at most 1 webhook per sensor."""
        from webmacs_backend.services import ingestion

        with patch.object(ingestion, "dispatch_event", new_callable=AsyncMock) as mock_dispatch:
            with patch.object(ingestion, "build_payload", return_value={"type": "sensor.reading"}):
                # Simulate 500 datapoints across 8 sensors
                for i in range(500):
                    sensor = f"sensor-{i % 8}"
                    ingestion._fire_webhook(sensor, float(i))

                await asyncio.sleep(0.05)
                # 8 sensors → max 8 dispatches (one per sensor)
                assert mock_dispatch.call_count == 8


# ─── Concurrency semaphore tests ────────────────────────────────────────────


class TestDispatchConcurrencyLimit:
    """Verify that the semaphore limits parallel outgoing HTTP requests."""

    async def test_semaphore_exists_and_limits(self) -> None:
        """_get_semaphore returns a semaphore with the configured limit."""
        from webmacs_backend.services import MAX_CONCURRENT_DELIVERIES, _get_semaphore

        sem = _get_semaphore()
        assert isinstance(sem, asyncio.Semaphore)
        # Internal counter should equal MAX_CONCURRENT_DELIVERIES
        assert sem._value == MAX_CONCURRENT_DELIVERIES

    async def test_concurrent_deliveries_are_bounded(self) -> None:
        """At most MAX_CONCURRENT_DELIVERIES run simultaneously."""
        from webmacs_backend.services import MAX_CONCURRENT_DELIVERIES, _dispatch_to_webhook

        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        original_inner = None
        # Import and patch the inner function
        import webmacs_backend.services as svc

        original_inner = svc._dispatch_to_webhook_inner

        async def slow_inner(webhook, event_type, payload):
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                if current_concurrent > max_concurrent:
                    max_concurrent = current_concurrent
            await asyncio.sleep(0.05)  # Simulate slow HTTP
            async with lock:
                current_concurrent -= 1

        with patch.object(svc, "_dispatch_to_webhook_inner", side_effect=slow_inner):
            # Create 20 dummy webhook objects
            from unittest.mock import MagicMock

            webhooks = []
            for i in range(20):
                wh = MagicMock()
                wh.id = i
                wh.url = f"https://example.com/hook-{i}"
                wh.secret = None
                wh.public_id = f"wh-{i}"
                webhooks.append(wh)

            from webmacs_backend.enums import WebhookEventType

            tasks = [
                _dispatch_to_webhook(wh, WebhookEventType.sensor_reading, {"test": True})
                for wh in webhooks
            ]
            await asyncio.gather(*tasks)

        # The semaphore should have prevented more than MAX_CONCURRENT_DELIVERIES
        assert max_concurrent <= MAX_CONCURRENT_DELIVERIES
        # But at least some ran concurrently (not fully serialized)
        assert max_concurrent > 1

    async def test_max_concurrent_deliveries_value(self) -> None:
        """MAX_CONCURRENT_DELIVERIES should be a reasonable bounded value."""
        from webmacs_backend.services import MAX_CONCURRENT_DELIVERIES

        # Must be > 0 (otherwise nothing dispatches)
        assert MAX_CONCURRENT_DELIVERIES > 0
        # Must be <= 50 (otherwise it's not really bounding anything)
        assert MAX_CONCURRENT_DELIVERIES <= 50


# ─── Integration: throttle interval is sane ──────────────────────────────────


class TestThrottleConfig:
    """Verify throttle configuration values are reasonable."""

    def test_sensor_webhook_interval_bounds(self) -> None:
        """_SENSOR_WEBHOOK_INTERVAL should be between 1s and 60s."""
        from webmacs_backend.services.ingestion import _SENSOR_WEBHOOK_INTERVAL

        assert 1.0 <= _SENSOR_WEBHOOK_INTERVAL <= 60.0

    def test_max_retries_bounded(self) -> None:
        """MAX_RETRIES should not cause exponential task explosion."""
        from webmacs_backend.services import MAX_RETRIES, RETRY_BACKOFF_BASE

        assert MAX_RETRIES <= 5
        # Worst case total wait: sum of backoff^attempt
        total_wait = sum(RETRY_BACKOFF_BASE**a for a in range(1, MAX_RETRIES + 1))
        # Should not exceed 5 minutes
        assert total_wait <= 300
