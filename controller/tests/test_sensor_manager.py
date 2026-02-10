"""Tests for sensor manager."""

import pytest
import respx
from httpx import Response

from webmacs_controller.schemas import EventSchema, EventType
from webmacs_controller.services.api_client import APIClient
from webmacs_controller.services.hardware import MockHardware
from webmacs_controller.services.sensor_manager import SensorManager


@pytest.mark.asyncio
async def test_sensor_manager_filters_sensors(sample_events: list[EventSchema], mock_hardware: MockHardware) -> None:
    async with APIClient(base_url="http://test:8000/api/v1") as client:
        revpi_mapping = {"sensor-temp-001": {"REVPI": "pt100_1", "TYPE": "temperature"}}
        mgr = SensorManager(sample_events, mock_hardware, client, revpi_mapping)
        assert len(mgr.sensors) == 2  # Two sensor-type events


@pytest.mark.asyncio
@respx.mock
async def test_sensor_manager_run_posts_batch(sample_events: list[EventSchema], mock_hardware: MockHardware) -> None:
    batch_route = respx.post("http://test:8000/api/v1/datapoints/batch").mock(
        return_value=Response(201, json={"status": "ok"})
    )
    async with APIClient(base_url="http://test:8000/api/v1") as client:
        client._token = "fake-token"
        revpi_mapping = {
            "sensor-temp-001": {"REVPI": "pt100_1", "TYPE": "temperature"},
            "sensor-press-001": {"REVPI": "pressure_1", "TYPE": "pressure"},
        }
        mgr = SensorManager(sample_events, mock_hardware, client, revpi_mapping)
        await mgr.run()
    assert batch_route.called
