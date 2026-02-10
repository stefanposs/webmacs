"""Sensor manager - reads sensor data and sends to backend."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from webmacs_controller.schemas import EventSchema, EventType

if TYPE_CHECKING:
    from webmacs_controller.services.telemetry import TelemetryTransport

logger = structlog.get_logger()


class SensorManager:
    """Manages sensor events - reads hardware, posts to backend."""

    def __init__(
        self,
        events: list[EventSchema],
        hardware: object,
        telemetry: TelemetryTransport,
        revpi_mapping: dict,
        is_production: bool = False,
    ) -> None:
        self._sensors = [e for e in events if e.type == EventType.sensor]
        self._hardware = hardware
        self._telemetry = telemetry
        self._revpi_mapping = revpi_mapping
        self._is_production = is_production
        logger.info("SensorManager initialized", sensor_count=len(self._sensors))

    @property
    def sensors(self) -> list[EventSchema]:
        return self._sensors

    async def run(self) -> None:
        """Read all sensor values from hardware and post to backend."""
        datapoints: list[dict] = []

        for sensor in self._sensors:
            revpi_label = self._get_revpi_label(sensor.public_id)
            if not revpi_label:
                continue

            value = self._hardware.read_value(revpi_label)
            if value is not None:
                datapoints.append({"value": value, "event_public_id": sensor.public_id})

        if datapoints:
            await self._telemetry.send(datapoints)
            logger.debug("Posted sensor data", count=len(datapoints))

    def _get_revpi_label(self, public_id: str) -> str | None:
        """Get hardware label for an event. Falls back to public_id in dev mode."""
        mapping = self._revpi_mapping.get(public_id)
        if mapping and mapping.get("REVPI"):
            return mapping["REVPI"]
        # Dev fallback: use public_id directly (SimulatedHardware registers by public_id)
        if not self._is_production:
            return public_id
        return None
