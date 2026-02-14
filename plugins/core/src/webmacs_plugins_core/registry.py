"""Plugin registry — manages plugin classes and their running instances."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from webmacs_plugins_core.discovery import discover_plugins
from webmacs_plugins_core.errors import PluginConfigError, PluginLoadError
from webmacs_plugins_core.health import HealthMonitor, HealthReport

if TYPE_CHECKING:
    from webmacs_plugins_core.base import DevicePlugin
    from webmacs_plugins_core.channels import ChannelDescriptor
    from webmacs_plugins_core.config import PluginMeta
    from webmacs_plugins_core.types import ChannelValue

logger = structlog.get_logger()


class PluginRegistry:
    """Central registry that manages plugin classes and their running instances.

    Usage::

        registry = PluginRegistry()
        registry.discover()  # scans entry_points
        registry.register_plugin_class(MyCustomPlugin)  # or add manually

        instance_id = registry.create_instance("revpi-dio", {"instance_name": "io-1", ...})
        await registry.connect_instance(instance_id)
        values = await registry.read_all_inputs()
    """

    def __init__(self, health_check_interval: float = 5.0) -> None:
        self._classes: dict[str, type[DevicePlugin]] = {}
        self._instances: dict[str, DevicePlugin] = {}
        self._health_monitor = HealthMonitor(check_interval=health_check_interval)
        self._log = logger.bind(component="plugin_registry")

    # ── Plugin class management ──────────────────────────────────────────

    def discover(self) -> dict[str, type[DevicePlugin]]:
        """Discover and register all installed plugin packages."""
        found = discover_plugins()
        self._classes.update(found)
        return found

    def register_plugin_class(self, cls: type[DevicePlugin]) -> None:
        """Manually register a plugin class (useful for testing or built-in plugins)."""
        meta: PluginMeta = cls.meta
        self._classes[meta.id] = cls
        self._log.info("plugin_class_registered", plugin_id=meta.id, name=meta.name)

    def get_available_plugins(self) -> list[PluginMeta]:
        """Return metadata for all registered plugin classes."""
        return [cls.meta for cls in self._classes.values()]

    def get_plugin_class(self, plugin_id: str) -> type[DevicePlugin] | None:
        return self._classes.get(plugin_id)

    # ── Instance management ──────────────────────────────────────────────

    def create_instance(self, plugin_id: str, config: dict[str, object], instance_id: str = "") -> str:
        """Create and configure a new plugin instance.

        Returns the instance_id (auto-generated if not provided).
        """
        cls = self._classes.get(plugin_id)
        if not cls:
            raise PluginLoadError(plugin_id, f"No plugin class registered with id '{plugin_id}'")

        plugin = cls()
        try:
            plugin.configure(config)
        except Exception as exc:
            raise PluginConfigError(plugin_id, str(exc)) from exc

        iid = instance_id or f"{plugin_id}-{len(self._instances) + 1}"
        self._instances[iid] = plugin
        self._health_monitor.track(iid, plugin)
        self._log.info("instance_created", instance_id=iid, plugin_id=plugin_id)
        return iid

    def get_instance(self, instance_id: str) -> DevicePlugin | None:
        return self._instances.get(instance_id)

    def list_instances(self) -> dict[str, DevicePlugin]:
        return dict(self._instances)

    def remove_instance(self, instance_id: str) -> bool:
        plugin = self._instances.pop(instance_id, None)
        if plugin is None:
            return False
        self._health_monitor.untrack(instance_id)
        self._log.info("instance_removed", instance_id=instance_id)
        return True

    # ── Instance operations ──────────────────────────────────────────────

    async def connect_instance(self, instance_id: str) -> None:
        plugin = self._instances.get(instance_id)
        if plugin:
            await plugin.connect()

    async def disconnect_instance(self, instance_id: str) -> None:
        plugin = self._instances.get(instance_id)
        if plugin:
            await plugin.disconnect()

    async def connect_all(self) -> None:
        """Connect all configured instances."""
        for iid, plugin in self._instances.items():
            try:
                await plugin.connect()
            except Exception as exc:
                self._log.error("instance_connect_failed", instance_id=iid, error=str(exc))

    async def disconnect_all(self) -> None:
        """Gracefully disconnect all instances (applies safe-state)."""
        for iid, plugin in self._instances.items():
            try:
                await plugin.disconnect()
            except Exception as exc:
                self._log.warning("instance_disconnect_error", instance_id=iid, error=str(exc))

    # ── Read / Write ─────────────────────────────────────────────────────

    async def read(self, instance_id: str, channel_id: str) -> ChannelValue | None:
        plugin = self._instances.get(instance_id)
        return await plugin.read(channel_id) if plugin else None

    async def write(self, instance_id: str, channel_id: str, value: ChannelValue) -> None:
        plugin = self._instances.get(instance_id)
        if plugin:
            await plugin.write(channel_id, value)

    async def read_all_inputs(self) -> list[dict[str, object]]:
        """Read all input channels from all connected instances.

        Returns a flat list of dicts suitable for telemetry::

            [{"instance_id": ..., "channel_id": ..., "value": ...}, ...]
        """
        results: list[dict[str, object]] = []
        for iid, plugin in self._instances.items():
            try:
                values = await plugin.read_all_inputs()
                for ch_id, value in values.items():
                    if value is not None:
                        results.append({"instance_id": iid, "channel_id": ch_id, "value": value})
            except Exception as exc:
                self._log.warning("read_all_error", instance_id=iid, error=str(exc))
        return results

    # ── Channel info ─────────────────────────────────────────────────────

    def get_channels(self, instance_id: str) -> dict[str, ChannelDescriptor]:
        plugin = self._instances.get(instance_id)
        return plugin.channels if plugin else {}

    def get_all_channels(self) -> dict[str, dict[str, ChannelDescriptor]]:
        """Return channels for all instances, keyed by instance_id."""
        return {iid: plugin.channels for iid, plugin in self._instances.items()}

    # ── Health ───────────────────────────────────────────────────────────

    @property
    def health_monitor(self) -> HealthMonitor:
        return self._health_monitor

    def get_health_reports(self) -> list[HealthReport]:
        return self._health_monitor.get_all_reports()
