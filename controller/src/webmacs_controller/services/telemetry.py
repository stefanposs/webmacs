"""Telemetry transport abstraction — HTTP and WebSocket implementations.

The controller can send sensor data via either HTTP POST (batch endpoint)
or WebSocket, controlled by the WEBMACS_TELEMETRY_MODE environment variable.
"""

from __future__ import annotations

import asyncio
from typing import Any, Protocol

import structlog

logger = structlog.get_logger()


class TelemetryTransport(Protocol):
    """Protocol for telemetry data transmission."""

    async def connect(self) -> None: ...
    async def send(self, datapoints: list[dict[str, Any]]) -> None: ...
    async def close(self) -> None: ...


class HttpTelemetry:
    """Send telemetry via HTTP POST to /datapoints/batch."""

    def __init__(self, api_client: Any) -> None:
        from webmacs_controller.services.api_client import APIClient
        self._api_client: APIClient = api_client

    async def connect(self) -> None:
        """No-op for HTTP — connection handled by httpx per request."""
        logger.info("telemetry_mode", mode="http")

    async def send(self, datapoints: list[dict[str, Any]]) -> None:
        await self._api_client.post("/datapoints/batch", {"datapoints": datapoints})

    async def close(self) -> None:
        """No-op — API client lifecycle managed by Application."""


class WebSocketTelemetry:
    """Send telemetry via persistent WebSocket connection.

    Implements auto-reconnect with exponential back-off.
    """

    def __init__(self, ws_url: str, auth_token_getter: Any = None) -> None:
        self._ws_url = ws_url
        self._get_token = auth_token_getter
        self._ws: Any = None
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 30.0

    async def connect(self) -> None:
        """Establish WebSocket connection to the backend."""
        logger.info("telemetry_mode", mode="websocket", url=self._ws_url)
        await self._ensure_connected()

    async def _ensure_connected(self) -> None:
        """Connect or reconnect with back-off."""
        import websockets

        if self._ws is not None:
            return

        delay = self._reconnect_delay
        while True:
            try:
                self._ws = await websockets.connect(self._ws_url)
                self._reconnect_delay = 1.0  # Reset on success
                logger.info("ws_telemetry_connected")
                return
            except Exception as e:
                logger.warning("ws_telemetry_connect_failed", error=str(e), retry_in=delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, self._max_reconnect_delay)

    async def send(self, datapoints: list[dict[str, Any]]) -> None:
        """Send a batch of datapoints via WebSocket."""
        import json

        try:
            await self._ensure_connected()
            if self._ws:
                await self._ws.send(json.dumps({"datapoints": datapoints}))
        except Exception as e:
            logger.warning("ws_telemetry_send_error", error=str(e))
            self._ws = None  # Force reconnect on next send
            raise

    async def close(self) -> None:
        """Close the WebSocket connection."""
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            finally:
                self._ws = None
            logger.info("ws_telemetry_closed")

    async def __aenter__(self) -> "WebSocketTelemetry":
        await self.connect()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()
