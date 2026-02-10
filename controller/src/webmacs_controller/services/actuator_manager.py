"""Actuator manager - receives commands from backend, writes to hardware."""

import structlog

from webmacs_controller.schemas import DatapointSchema, EventSchema, EventType
from webmacs_controller.services.api_client import APIClient
from webmacs_controller.services.hardware import HardwareInterface

logger = structlog.get_logger()


class ActuatorManager:
    """Manages actuator events - reads from backend, writes to hardware."""

    def __init__(self, events: list[EventSchema], hardware: HardwareInterface, api_client: APIClient, revpi_mapping: dict) -> None:
        self._actuators = [
            e for e in events if e.type in (EventType.actuator, EventType.range)
        ]
        self._hardware = hardware
        self._api_client = api_client
        self._revpi_mapping = revpi_mapping
        logger.info("ActuatorManager initialized", actuator_count=len(self._actuators))

    @property
    def actuators(self) -> list[EventSchema]:
        return self._actuators

    async def run(self) -> None:
        """Fetch latest actuator values from backend and write to hardware."""
        try:
            latest = await self._api_client.get("/datapoints/latest")
            if not isinstance(latest, list):
                return

            for dp_data in latest:
                dp = DatapointSchema(**dp_data) if isinstance(dp_data, dict) else dp_data
                for actuator in self._actuators:
                    if dp.event_public_id == actuator.public_id:
                        revpi_label = self._get_revpi_label(actuator.public_id)
                        if revpi_label:
                            self._hardware.write_value(revpi_label, dp.value)
                            logger.debug("Actuator updated", label=revpi_label, value=dp.value)

        except Exception as e:
            logger.error("ActuatorManager run failed", error=str(e))

    def _get_revpi_label(self, public_id: str) -> str | None:
        mapping = self._revpi_mapping.get(public_id)
        return mapping["REVPI"] if mapping and mapping.get("REVPI") else None
