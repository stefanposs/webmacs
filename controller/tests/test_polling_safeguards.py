"""Tests for sub-second polling safeguards.

Covers:
- PluginBridge per-sensor throttle (skips reads that arrive too soon)
- PluginBridge dedup (drops unchanged values when enabled)
- PluginBridge batch chunking (splits oversized batches)
- APIClient 429 retry with Retry-After header
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
import respx
from httpx import Response

from webmacs_controller.config import ControllerSettings
from webmacs_controller.services.api_client import APIClient, APIClientError
from webmacs_controller.services.plugin_bridge import ChannelEventMap, PluginBridge

BASE = "http://test:8000/api/v1"


# ---------------------------------------------------------------------------
# Helpers — lightweight mocks
# ---------------------------------------------------------------------------


def _make_settings(**overrides: Any) -> ControllerSettings:
    defaults: dict[str, Any] = {
        "env": "development",
        "server_url": "http://localhost",
        "server_port": 8000,
        "admin_email": "t@t.io",
        "admin_password": "p",
        "poll_interval": 1.0,
        "request_timeout": 5.0,
        "max_batch_size": 100,
        "dedup_enabled": False,
    }
    defaults.update(overrides)
    return ControllerSettings(**defaults)


def _make_bridge(
    settings: ControllerSettings | None = None,
) -> tuple[PluginBridge, AsyncMock]:
    """Create a PluginBridge with a mock telemetry transport."""
    api = AsyncMock()
    telemetry = AsyncMock()
    telemetry.send = AsyncMock()
    bridge = PluginBridge(api, telemetry, settings=settings or _make_settings())
    # Mark as initialized so read_and_send actually runs
    bridge._initialized = True
    return bridge, telemetry


# ---------------------------------------------------------------------------
# Per-sensor throttle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_throttle_skips_too_soon() -> None:
    """Sensors read within poll_interval are silently dropped."""
    settings = _make_settings(poll_interval=1.0)
    bridge, telemetry = _make_bridge(settings)

    # Map one channel
    bridge._channel_map.add("inst1", "ch1", "evt-1")

    # Simulate registry returning same sensor twice
    bridge._registry = AsyncMock()
    entry = {"instance_id": "inst1", "channel_id": "ch1", "value": 42.0}
    bridge._registry.read_all_inputs = AsyncMock(return_value=[entry])

    # First call — accepted
    await bridge.read_and_send()
    assert telemetry.send.call_count == 1
    assert telemetry.send.call_args[0][0] == [{"value": 42.0, "event_public_id": "evt-1"}]

    # Second call immediately — throttled (< 1.0s elapsed)
    telemetry.send.reset_mock()
    await bridge.read_and_send()
    assert telemetry.send.call_count == 0


@pytest.mark.asyncio
async def test_throttle_allows_after_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    """After poll_interval elapses, the sensor is read again."""
    import time as _time

    settings = _make_settings(poll_interval=0.5)
    bridge, telemetry = _make_bridge(settings)

    bridge._channel_map.add("inst1", "ch1", "evt-1")
    bridge._registry = AsyncMock()
    bridge._registry.read_all_inputs = AsyncMock(
        return_value=[{"instance_id": "inst1", "channel_id": "ch1", "value": 10.0}]
    )

    # First read
    await bridge.read_and_send()
    assert telemetry.send.call_count == 1

    # Pretend time advanced past poll_interval
    bridge._last_read[("inst1", "ch1")] = _time.monotonic() - 1.0

    telemetry.send.reset_mock()
    await bridge.read_and_send()
    assert telemetry.send.call_count == 1


# ---------------------------------------------------------------------------
# Dedup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dedup_drops_unchanged_value(monkeypatch: pytest.MonkeyPatch) -> None:
    """With dedup_enabled, repeated identical values are dropped."""
    import time as _time

    settings = _make_settings(poll_interval=0.2, dedup_enabled=True)
    bridge, telemetry = _make_bridge(settings)

    bridge._channel_map.add("inst1", "ch1", "evt-1")
    bridge._registry = AsyncMock()
    bridge._registry.read_all_inputs = AsyncMock(
        return_value=[{"instance_id": "inst1", "channel_id": "ch1", "value": 5.0}]
    )

    # First read — always accepted
    await bridge.read_and_send()
    assert telemetry.send.call_count == 1

    # Simulate enough time passing
    bridge._last_read[("inst1", "ch1")] = _time.monotonic() - 1.0

    # Same value → dedup drops it
    telemetry.send.reset_mock()
    await bridge.read_and_send()
    assert telemetry.send.call_count == 0


@pytest.mark.asyncio
async def test_dedup_allows_changed_value(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dedup lets through a value that differs from the last one."""
    import time as _time

    settings = _make_settings(poll_interval=0.2, dedup_enabled=True)
    bridge, telemetry = _make_bridge(settings)

    bridge._channel_map.add("inst1", "ch1", "evt-1")
    bridge._registry = AsyncMock()
    bridge._registry.read_all_inputs = AsyncMock(
        return_value=[{"instance_id": "inst1", "channel_id": "ch1", "value": 5.0}]
    )

    await bridge.read_and_send()
    assert telemetry.send.call_count == 1

    bridge._last_read[("inst1", "ch1")] = _time.monotonic() - 1.0

    # Change value
    bridge._registry.read_all_inputs = AsyncMock(
        return_value=[{"instance_id": "inst1", "channel_id": "ch1", "value": 6.0}]
    )

    telemetry.send.reset_mock()
    await bridge.read_and_send()
    assert telemetry.send.call_count == 1


# ---------------------------------------------------------------------------
# Batch chunking
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chunking_splits_large_batch() -> None:
    """Batches larger than max_batch_size are split into multiple sends."""
    settings = _make_settings(max_batch_size=3, poll_interval=0.2)
    bridge, telemetry = _make_bridge(settings)

    # Create 7 mapped channels
    entries = []
    for i in range(7):
        iid, ch = f"inst{i}", f"ch{i}"
        bridge._channel_map.add(iid, ch, f"evt-{i}")
        entries.append({"instance_id": iid, "channel_id": ch, "value": float(i)})

    bridge._registry = AsyncMock()
    bridge._registry.read_all_inputs = AsyncMock(return_value=entries)

    await bridge.read_and_send()

    # 7 datapoints / batch_size 3 → 3 send calls (3 + 3 + 1)
    assert telemetry.send.call_count == 3
    sizes = [len(call.args[0]) for call in telemetry.send.call_args_list]
    assert sizes == [3, 3, 1]


# ---------------------------------------------------------------------------
# APIClient 429 retry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_429_retried_with_backoff() -> None:
    """429 Too Many Requests is retried (like 5xx), not treated as fatal."""
    route = respx.get(f"{BASE}/events").mock(
        side_effect=[
            Response(429, json={"detail": "rate limited"}, headers={"Retry-After": "0"}),
            Response(200, json={"data": []}),
        ]
    )
    async with APIClient(base_url=BASE, max_retries=3, backoff_base=0) as client:
        client._token = "tok"
        result = await client.get("/events")
    assert result == {"data": []}
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_429_exhausts_retries() -> None:
    """Persistent 429 exhausts retries and raises APIClientError."""
    respx.get(f"{BASE}/events").mock(
        return_value=Response(429, json={"detail": "rate limited"}, headers={"Retry-After": "0"}),
    )
    async with APIClient(base_url=BASE, max_retries=2, backoff_base=0) as client:
        client._token = "tok"
        with pytest.raises(APIClientError, match="2 attempts"):
            await client.get("/events")


@pytest.mark.asyncio
@respx.mock
async def test_429_uses_retry_after_header() -> None:
    """When Retry-After is present, the client respects it."""
    route = respx.post(f"{BASE}/datapoints/batch").mock(
        side_effect=[
            Response(429, json={"detail": "slow down"}, headers={"Retry-After": "0"}),
            Response(201, json={"status": "success"}),
        ]
    )
    async with APIClient(base_url=BASE, max_retries=3, backoff_base=0) as client:
        client._token = "tok"
        result = await client.post("/datapoints/batch", json={"datapoints": []})
    assert result == {"status": "success"}
    assert route.call_count == 2
