"""Plugin health monitoring — tracks connection status and triggers reconnection."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog

from webmacs_plugins_core.types import PluginState

if TYPE_CHECKING:
    from webmacs_plugins_core.base import DevicePlugin

logger = structlog.get_logger()


@dataclass
class HealthReport:
    """Snapshot of a plugin instance's health."""

    plugin_id: str
    instance_name: str
    state: PluginState
    error_count: int = 0
    last_error: str | None = None
    channel_count: int = 0
    demo_mode: bool = False
    reconnect_attempts: int = 0

    @property
    def is_healthy(self) -> bool:
        return self.state in (PluginState.connected, PluginState.running)

    def to_dict(self) -> dict[str, object]:
        return {
            "plugin_id": self.plugin_id,
            "instance_name": self.instance_name,
            "state": str(self.state),
            "error_count": self.error_count,
            "last_error": self.last_error,
            "channel_count": self.channel_count,
            "demo_mode": self.demo_mode,
            "is_healthy": self.is_healthy,
            "reconnect_attempts": self.reconnect_attempts,
        }


@dataclass
class _TrackedPlugin:
    plugin: DevicePlugin
    reconnect_attempts: int = 0
    max_attempts: int = 5
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0


class HealthMonitor:
    """Monitors plugin instances and automatically triggers reconnection.

    Run as an ``asyncio.Task`` alongside the sensor/actuator loops.
    """

    def __init__(self, check_interval: float = 5.0) -> None:
        self._tracked: dict[str, _TrackedPlugin] = {}
        self._check_interval = check_interval
        self._log = logger.bind(component="health_monitor")

    def track(self, instance_id: str, plugin: DevicePlugin) -> None:
        retry = plugin.config.retry_policy if plugin.config else None
        self._tracked[instance_id] = _TrackedPlugin(
            plugin=plugin,
            max_attempts=retry.max_attempts if retry else 5,
            base_delay=retry.base_delay if retry else 1.0,
            max_delay=retry.max_delay if retry else 60.0,
            backoff_factor=retry.backoff_factor if retry else 2.0,
        )

    def untrack(self, instance_id: str) -> None:
        self._tracked.pop(instance_id, None)

    def get_all_reports(self) -> list[HealthReport]:
        reports = []
        for tracked in self._tracked.values():
            report = tracked.plugin.health_check()
            report.reconnect_attempts = tracked.reconnect_attempts
            reports.append(report)
        return reports

    async def run(self) -> None:
        """Main health monitoring loop — runs until cancelled."""
        self._log.info("health_monitor_started")
        try:
            while True:
                await asyncio.sleep(self._check_interval)
                await self._check_all()
        except asyncio.CancelledError:
            self._log.info("health_monitor_stopped")

    async def _check_all(self) -> None:
        for instance_id, tracked in list(self._tracked.items()):
            plugin = tracked.plugin
            if plugin.state == PluginState.error:
                await self._handle_unhealthy(instance_id, tracked)

    async def _handle_unhealthy(self, instance_id: str, tracked: _TrackedPlugin) -> None:
        if tracked.max_attempts > 0 and tracked.reconnect_attempts >= tracked.max_attempts:
            return  # Give up after max attempts

        tracked.reconnect_attempts += 1
        delay = min(
            tracked.base_delay * (tracked.backoff_factor ** (tracked.reconnect_attempts - 1)),
            tracked.max_delay,
        )
        self._log.info(
            "plugin_reconnecting",
            instance=instance_id,
            attempt=tracked.reconnect_attempts,
            delay=delay,
        )
        await asyncio.sleep(delay)
        try:
            await tracked.plugin.connect()
            tracked.reconnect_attempts = 0
            self._log.info("plugin_reconnected", instance=instance_id)
        except Exception as exc:
            self._log.warning("plugin_reconnect_failed", instance=instance_id, error=str(exc))
