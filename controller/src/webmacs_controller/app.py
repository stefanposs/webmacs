"""Controller application orchestrator - manages all async service loops."""

import asyncio
import signal
from collections.abc import Callable, Coroutine
from typing import Any

import structlog

from webmacs_controller.config import ControllerSettings
from webmacs_controller.schemas import EventSchema
from webmacs_controller.services.actuator_manager import ActuatorManager
from webmacs_controller.services.api_client import APIClient
from webmacs_controller.services.demo_seeder import DemoSeeder
from webmacs_controller.services.hardware import HardwareInterface, RevPiHardware, SimulatedHardware
from webmacs_controller.services.rule_engine import RuleEngine
from webmacs_controller.services.sensor_manager import SensorManager
from webmacs_controller.services.telemetry import HttpTelemetry, WebSocketTelemetry

logger = structlog.get_logger()


class Application:
    """Main controller application with concurrent async loops."""

    def __init__(self, settings: ControllerSettings | None = None) -> None:
        self._settings = settings or ControllerSettings()
        self._running = False
        self._api_client: APIClient | None = None
        self._telemetry: HttpTelemetry | WebSocketTelemetry | None = None

    async def run(self) -> None:
        """Initialize services and run concurrent loops until shutdown."""
        self._running = True
        self._setup_signal_handlers()

        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.add_log_level,
                structlog.dev.ConsoleRenderer(),
            ],
        )

        logger.info(
            "Controller starting",
            server=self._settings.server_url,
            environment="production" if self._settings.is_production else "development",
        )

        self._api_client = APIClient(
            base_url=self._settings.base_url,
            timeout=self._settings.request_timeout,
        )

        try:
            # 1. Authenticate
            await self._api_client.login(
                self._settings.admin_email,
                self._settings.admin_password,
            )
            logger.info("Authenticated with backend")

            # 2. Seed demo events in dev mode
            if not self._settings.is_production:
                seeder = DemoSeeder(self._api_client)
                await seeder.seed_if_empty()

            # 3. Fetch events
            events = await self._fetch_events()
            logger.info("Events loaded", count=len(events))

            # 4. Build RevPi mapping from config
            revpi_mapping = self._settings.revpi_mapping

            # 5. Create hardware interface
            hardware = self._create_hardware(events)

            # 6. Create telemetry transport
            if self._settings.telemetry_mode == "websocket":
                self._telemetry = WebSocketTelemetry(self._settings.ws_url)
                await self._telemetry.connect()
                logger.info("Telemetry via WebSocket", url=self._settings.ws_url)
            else:
                self._telemetry = HttpTelemetry(self._api_client)
                await self._telemetry.connect()
                logger.info("Telemetry via HTTP")

            # 7. Create service instances
            sensor_mgr = SensorManager(
                events,
                hardware,
                self._telemetry,
                revpi_mapping,
                is_production=self._settings.is_production,
            )
            actuator_mgr = ActuatorManager(events, hardware, self._api_client, revpi_mapping)
            rule_engine = RuleEngine(
                events,
                hardware,
                self._api_client,
                rule_event_id=self._settings.rule_event_id,
            )

            # 7. Run concurrent loops
            # Post startup log to backend
            await self._post_log("Controller started – sensor polling active", "info")

            logger.info("Starting service loops")
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self._loop("sensor", sensor_mgr.run))
                tg.create_task(self._loop("actuator", actuator_mgr.run))
                tg.create_task(self._loop("rule", rule_engine.run))

        except* KeyboardInterrupt:
            logger.info("Shutdown requested via keyboard")
        except* Exception as eg:
            for exc in eg.exceptions:
                logger.exception("Fatal error", error=str(exc), type=type(exc).__name__)
        finally:
            await self._shutdown()

    async def _loop(
        self,
        name: str,
        coro_fn: Callable[[], Coroutine[Any, Any, None]],
        backoff_base: float = 1.0,
        max_backoff: float = 60.0,
    ) -> None:
        """Run a service coroutine in a loop with exponential backoff on errors."""
        consecutive_errors = 0
        while self._running:
            try:
                await coro_fn()
                consecutive_errors = 0
            except Exception as e:
                consecutive_errors += 1
                wait = min(backoff_base * (2**consecutive_errors), max_backoff)
                logger.warning(
                    f"{name} loop error, backing off",
                    error=str(e),
                    wait_seconds=wait,
                    consecutive_errors=consecutive_errors,
                )
                await asyncio.sleep(wait)
                continue

            await asyncio.sleep(self._settings.poll_interval)

    async def _fetch_events(self) -> list[EventSchema]:
        """Fetch all events from the backend API."""
        assert self._api_client is not None
        data = await self._api_client.get("/events")
        if isinstance(data, dict) and "data" in data:
            return [EventSchema(**e) for e in data["data"]]
        if isinstance(data, list):
            return [EventSchema(**e) for e in data]
        return []

    def _create_hardware(self, events: list[EventSchema]) -> HardwareInterface:
        """Create the appropriate hardware interface."""
        if self._settings.is_production:
            try:
                return RevPiHardware()
            except Exception as e:
                logger.warning("RevPi unavailable, falling back to simulated", error=str(e))
        return SimulatedHardware(events, self._settings.revpi_mapping)

    def _setup_signal_handlers(self) -> None:
        """Register graceful shutdown handlers."""
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._request_shutdown)

    def _request_shutdown(self) -> None:
        """Flag the application for graceful shutdown."""
        logger.info("Shutdown signal received")
        self._running = False

    async def _post_log(self, content: str, logging_type: str = "info") -> None:
        """Post a log entry to the backend."""
        try:
            if self._api_client:
                await self._api_client.post("/logging", {"content": content, "logging_type": logging_type})
        except Exception:
            pass  # best-effort, don't crash the controller

    async def _shutdown(self) -> None:
        """Clean up resources."""
        logger.info("Shutting down...")
        if self._telemetry:
            await self._telemetry.close()
        if self._api_client:
            await self._post_log("Controller shutting down", "warning")
            await self._api_client.close()
        logger.info("Controller stopped")
