"""Controller test configuration and fixtures."""

import pytest

from webmacs_controller.config import ControllerSettings
from webmacs_controller.schemas import EventSchema, EventType
from webmacs_controller.services.hardware import MockHardware


@pytest.fixture
def settings() -> ControllerSettings:
    return ControllerSettings(
        env="development",
        server_url="http://localhost",
        server_port=8000,
        admin_email="test@example.com",
        admin_password="testpass",
        poll_interval=0.01,
        request_timeout=5.0,
        rule_event_id="rule-001",
        revpi_mapping={
            "sensor-temp-001": {"REVPI": "pt100_1", "TYPE": "temperature"},
            "actuator-valve-001": {"REVPI": "valve1", "TYPE": "valve"},
        },
    )


@pytest.fixture
def mock_hardware() -> MockHardware:
    return MockHardware()


@pytest.fixture
def sample_events() -> list[EventSchema]:
    return [
        EventSchema(
            public_id="sensor-temp-001",
            name="Temperature Sensor 1",
            type=EventType.sensor,
            unit="°C",
            min_value=0.0,
            max_value=200.0,
        ),
        EventSchema(
            public_id="sensor-press-001",
            name="Pressure Sensor 1",
            type=EventType.sensor,
            unit="bar",
            min_value=0.0,
            max_value=10.0,
        ),
        EventSchema(
            public_id="actuator-valve-001",
            name="Valve 1",
            type=EventType.actuator,
            unit="",
            min_value=0.0,
            max_value=1.0,
        ),
        EventSchema(
            public_id="rule-001",
            name="Rule Valve",
            type=EventType.range,
            unit="",
            min_value=0.0,
            max_value=100.0,
        ),
        EventSchema(
            public_id="opened-001",
            name="Open Duration",
            type=EventType.cmd_opened,
            unit="s",
            min_value=0.0,
            max_value=60.0,
        ),
        EventSchema(
            public_id="closed-001",
            name="Close Duration",
            type=EventType.cmd_closed,
            unit="s",
            min_value=0.0,
            max_value=60.0,
        ),
        EventSchema(
            public_id="start-001",
            name="Start Button",
            type=EventType.cmd_button,
            unit="",
            min_value=0.0,
            max_value=1.0,
        ),
    ]
