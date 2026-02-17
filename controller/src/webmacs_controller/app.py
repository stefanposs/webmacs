"""Controller application orchestrator - manages all async service loops."""

from __future__ import annotations

import asyncio
import signal
from collections.abc import Callable, Coroutine
from typing import Any

import structlog

from webmacs_controller.config import ControllerSettings
from webmacs_controller.schemas import EventSchema
from webmacs_controller.services.api_client import APIClient
from webmacs_controller.services.plugin_bridge import PluginBridge
from webmacs_controller.services.rule_engine import RuleEngine
from webmacs_controller.services.telemetry import HttpTelemetry, WebSocketTelemetry

logger = structlog.get_logger()


class Application:
    """Main controller application with concurrent async loops."""

    def __init__(self, settings: ControllerSettings | None = None) -> None:
        self._settings = settings or ControllerSettings()
        self._running = False
        self._api_client: APIClient | None = None
        self._telemetry: HttpTelemetry | WebSocketTelemetry | None = None
        self._plugin_bridge: PluginBridge | None = None

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

            # 2. In dev mode, auto-register a simulated plugin if no instances exist
            if not self._settings.is_production:
                await self._ensure_dev_plugin()

            # 3. Fetch events (still needed for RuleEngine)
            events = await self._fetch_events()
            logger.info("Events loaded", count=len(events))

            # 4. Create telemetry transport
            if self._settings.telemetry_mode == "websocket":
                self._telemetry = WebSocketTelemetry(
                    self._settings.ws_url,
                    auth_token_getter=lambda: self._api_client.auth_token if self._api_client else None,
                )
                await self._telemetry.connect()
                logger.info("Telemetry via WebSocket", url=self._settings.ws_url)
            else:
                self._telemetry = HttpTelemetry(self._api_client)
                await self._telemetry.connect()
                logger.info("Telemetry via HTTP")

            # 5. Create rule engine (uses API client only, no hardware dependency)
            rule_engine = RuleEngine(
                events,
                self._api_client,
                rule_event_id=self._settings.rule_event_id,
            )

            # 6. Initialize plugin bridge (sole sensor/actuator path)
            self._plugin_bridge = PluginBridge(self._api_client, self._telemetry, settings=self._settings)
            await self._plugin_bridge.initialize()
            logger.info("Plugin bridge initialized")

            # 7. Run concurrent loops
            await self._post_log("Controller started – plugin sensor polling active", "info")

            logger.info("Starting service loops")
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self._loop("rule", rule_engine.run))
                tg.create_task(self._loop("plugin_sensor", self._plugin_bridge.read_and_send))
                tg.create_task(self._loop("plugin_actuator", self._plugin_bridge.receive_and_write))
                tg.create_task(
                    self._loop(
                        "plugin_sync",
                        self._plugin_bridge.sync,
                        fixed_interval=self._settings.plugin_sync_interval,
                    )
                )

        except* KeyboardInterrupt:
            logger.info("Shutdown requested via keyboard")
        except* Exception as eg:
            for exc in eg.exceptions:
                logger.exception(
                    "Fatal error",
                    error=str(exc),
                    type=type(exc).__name__,
                )
        finally:
            await self._shutdown()

    async def _ensure_dev_plugin(self) -> None:
        """In development mode, create a Simulated Device plugin on first boot only.

        Skips seeding if:
        - auto_seed_plugins is disabled via WEBMACS_AUTO_SEED=false
        - plugin instances already exist
        - events already exist (user has configured the system before)
        """
        assert self._api_client is not None

        if not self._settings.auto_seed_plugins:
            logger.info("Auto-seeding disabled via WEBMACS_AUTO_SEED=false")
            return

        try:
            instances = await self._api_client.fetch_plugin_instances()
            if instances:
                logger.info("Plugin instances already exist, skipping dev auto-setup", count=len(instances))
                return

            # Check if events exist — if so, the user previously configured
            # and intentionally removed all plugins; do not re-seed.
            events = await self._api_client.get("/events")
            event_list = events.get("data", []) if isinstance(events, dict) else events
            if event_list:
                logger.info(
                    "Events exist but no plugins — user removed plugins intentionally, skipping auto-seed",
                    event_count=len(event_list),
                )
                return

            logger.info("First boot detected — creating Simulated Device for development")
            await self._api_client.create_plugin_instance(
                plugin_id="simulated",
                instance_name="Simulated Device",
                demo_mode=True,
                enabled=True,
            )
            logger.info("Simulated Device plugin instance created with auto-linked events")

            # Seed initial log entries
            await self._post_log("Controller started in development mode", "info")
            await self._post_log("Simulated Device plugin auto-registered with 9 channels", "info")
        except Exception as exc:
            logger.warning("Dev plugin auto-setup failed", error=str(exc))

    async def _loop(
        self,
        name: str,
        coro_fn: Callable[[], Coroutine[Any, Any, None]],
        backoff_base: float = 1.0,
        max_backoff: float = 60.0,
        fixed_interval: float | None = None,
    ) -> None:
        """Run a service coroutine in a loop with exponential backoff on errors.

        If *fixed_interval* is set, it overrides ``poll_interval`` for the
        sleep between successful iterations (useful for slower sync loops).
        """
        consecutive_errors = 0
        interval = fixed_interval if fixed_interval is not None else self._settings.poll_interval
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

            await asyncio.sleep(interval)

    async def _fetch_events(self) -> list[EventSchema]:
        """Fetch all events from the backend API."""
        assert self._api_client is not None
        data = await self._api_client.get("/events")
        if isinstance(data, dict) and "data" in data:
            return [EventSchema(**e) for e in data["data"]]
        if isinstance(data, list):
            return [EventSchema(**e) for e in data]
        return []

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
            logger.debug("post_log_failed", exc_info=True)

    async def _shutdown(self) -> None:
        """Clean up resources."""
        logger.info("Shutting down...")
        if self._plugin_bridge:
            await self._plugin_bridge.shutdown()
        if self._telemetry:
            await self._telemetry.close()
        if self._api_client:
            await self._post_log("Controller shutting down", "warning")
            await self._api_client.close()
        logger.info("Controller stopped")
