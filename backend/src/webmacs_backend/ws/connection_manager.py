"""WebSocket connection manager — pub/sub hub for real-time data distribution.

Manages two independent groups:
  - 'controller': Incoming telemetry from IoT controller(s)
  - 'frontend':   Browser clients subscribing to live datapoint streams
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog
from fastapi import WebSocket

logger = structlog.get_logger()


class ConnectionManager:
    """Thread-safe WebSocket connection manager with topic-based pub/sub."""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, topic: str, ws: WebSocket) -> None:
        """Accept a WebSocket and register it under a topic."""
        await ws.accept()
        async with self._lock:
            if topic not in self._connections:
                self._connections[topic] = set()
            self._connections[topic].add(ws)
        logger.info("ws_connected", topic=topic, clients=len(self._connections[topic]))

    async def disconnect(self, topic: str, ws: WebSocket) -> None:
        """Remove a WebSocket from a topic."""
        async with self._lock:
            conns = self._connections.get(topic)
            if conns:
                conns.discard(ws)
                if not conns:
                    del self._connections[topic]
        logger.info("ws_disconnected", topic=topic)

    async def broadcast(self, topic: str, data: Any) -> None:
        """Send JSON data to all connections in a topic."""
        async with self._lock:
            conns = list(self._connections.get(topic, set()))

        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)

        # Clean up dead connections
        if dead:
            async with self._lock:
                topic_set = self._connections.get(topic)
                if topic_set:
                    for ws in dead:
                        topic_set.discard(ws)

    @property
    def frontend_count(self) -> int:
        return len(self._connections.get("frontend", set()))

    @property
    def controller_count(self) -> int:
        return len(self._connections.get("controller", set()))


# Singleton instance — imported by endpoints and app
manager = ConnectionManager()
