"""Demo event seeder for development mode."""

from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from webmacs_controller.services.api_client import APIClient

logger = structlog.get_logger()

# Realistic demo events for a fluidized bed (Wirbelschicht) lab experiment
DEMO_EVENTS: list[dict[str, Any]] = [
    {"name": "Temperature Reactor", "min_value": 20.0, "max_value": 500.0, "unit": "°C", "type": "sensor"},
    {"name": "Temperature Inlet", "min_value": 15.0, "max_value": 200.0, "unit": "°C", "type": "sensor"},
    {"name": "Temperature Outlet", "min_value": 15.0, "max_value": 300.0, "unit": "°C", "type": "sensor"},
    {"name": "Pressure Chamber", "min_value": 0.0, "max_value": 6.0, "unit": "bar", "type": "sensor"},
    {"name": "Pressure Differential", "min_value": 0.0, "max_value": 100.0, "unit": "mbar", "type": "sensor"},
    {"name": "Volume Flow", "min_value": 0.0, "max_value": 40.0, "unit": "m³/h", "type": "sensor"},
    {"name": "Humidity", "min_value": 0.0, "max_value": 100.0, "unit": "%", "type": "sensor"},
    {"name": "Heater Power", "min_value": 0.0, "max_value": 100.0, "unit": "%", "type": "actuator"},
    {"name": "Valve Position", "min_value": 0.0, "max_value": 100.0, "unit": "%", "type": "actuator"},
]


class DemoSeeder:
    """Seeds the backend with demo events if none exist. Dev mode only."""

    def __init__(self, api_client: APIClient) -> None:
        self._api_client = api_client

    async def seed_if_empty(self) -> list[str]:
        """Create demo events if the backend has none.

        Returns list of created event names (empty if events already existed).
        """
        existing = await self._api_client.get("/events")

        # Handle paginated response
        items = existing.get("data", []) if isinstance(existing, dict) else existing or []

        if items:
            logger.info("Events already exist, skipping demo seed", count=len(items))
            return []

        created: list[str] = []
        for event_data in DEMO_EVENTS:
            try:
                await self._api_client.post("/events", event_data)
                created.append(event_data["name"])
                logger.info("Seeded demo event", name=event_data["name"])
            except Exception as e:
                logger.warning("Failed to seed event", name=event_data["name"], error=str(e))

        logger.info("Demo seeding complete", created=len(created))

        # Seed initial log entries so the Logs view isn't empty
        await self._seed_logs()

        return created

    async def _seed_logs(self) -> None:
        """Seed some initial log entries."""
        demo_logs = [
            {"content": "Controller started in development mode", "logging_type": "info"},
            {"content": "Demo events seeded successfully", "logging_type": "info"},
            {"content": "Simulated hardware initialized", "logging_type": "info"},
            {"content": "Sensor polling active – 8 channels", "logging_type": "info"},
            {"content": "Actuator manager ready – 2 channels", "logging_type": "info"},
        ]
        for entry in demo_logs:
            try:
                await self._api_client.post("/logging", entry)
            except Exception as e:
                logger.warning("Failed to seed log entry", error=str(e))
