"""Plugin bridge — connects the PluginRegistry to backend events and telemetry.

This service replaces the legacy HardwareInterface-based sensor/actuator
flow for plugin-managed channels:

1. Discovers & connects all plugin instances from the backend.
2. Reads all plugin input channels and maps them to events for telemetry.
3. Receives actuator values from the backend and writes them to plugin outputs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from webmacs_plugins_core.registry import PluginRegistry

if TYPE_CHECKING:
    from webmacs_controller.services.api_client import APIClient
    from webmacs_controller.services.telemetry import TelemetryTransport

logger = structlog.get_logger()


class ChannelEventMap:
    """Bi-directional mapping between plugin channels and backend events."""

    def __init__(self) -> None:
        # (instance_id, channel_id) → event_public_id
        self._to_event: dict[tuple[str, str], str] = {}
        # event_public_id → (instance_id, channel_id)
        self._to_channel: dict[str, tuple[str, str]] = {}

    def add(self, instance_id: str, channel_id: str, event_public_id: str) -> None:
        key = (instance_id, channel_id)
        self._to_event[key] = event_public_id
        self._to_channel[event_public_id] = key

    def event_for(self, instance_id: str, channel_id: str) -> str | None:
        return self._to_event.get((instance_id, channel_id))

    def channel_for(self, event_public_id: str) -> tuple[str, str] | None:
        return self._to_channel.get(event_public_id)

    @property
    def mapped_events(self) -> set[str]:
        return set(self._to_channel.keys())

    def __len__(self) -> int:
        return len(self._to_event)


class PluginBridge:
    """Bridge between the plugin system and the controller's event/telemetry layer.

    Usage::

        bridge = PluginBridge(api_client, telemetry)
        await bridge.initialize()       # discover, configure, connect
        await bridge.read_and_send()     # sensor loop tick
        await bridge.receive_and_write() # actuator loop tick
        await bridge.shutdown()          # graceful disconnect
    """

    def __init__(
        self,
        api_client: APIClient,
        telemetry: TelemetryTransport,
    ) -> None:
        self._api = api_client
        self._telemetry = telemetry
        self._registry = PluginRegistry()
        self._channel_map = ChannelEventMap()
        self._initialized = False

    @property
    def registry(self) -> PluginRegistry:
        return self._registry

    @property
    def channel_map(self) -> ChannelEventMap:
        return self._channel_map

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    # ── Initialization ───────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Discover plugins, fetch instances from backend, connect them."""
        # 1. Discover installed plugin packages
        found = self._registry.discover()
        logger.info("plugins_discovered", count=len(found), ids=list(found.keys()))

        # 2. Fetch configured instances from the backend
        instances = await self._api.fetch_plugin_instances()
        if not instances:
            logger.info("no_plugin_instances_configured")
            return

        # 3. Create & connect each enabled instance
        for inst in instances:
            plugin_id = inst.get("plugin_id", "")
            public_id = inst.get("public_id", "")
            instance_name = inst.get("instance_name", plugin_id)
            demo_mode = inst.get("demo_mode", True)
            enabled = inst.get("enabled", True)
            config_json = inst.get("config_json") or {}

            if not enabled:
                logger.info("plugin_instance_disabled", instance=instance_name, plugin_id=plugin_id)
                continue

            if not self._registry.get_plugin_class(plugin_id):
                logger.warning("plugin_class_not_found", plugin_id=plugin_id, instance=instance_name)
                continue

            config: dict[str, object] = {
                "instance_name": instance_name,
                "demo_mode": demo_mode,
            }
            if isinstance(config_json, dict):
                config.update(config_json)

            try:
                iid = self._registry.create_instance(plugin_id, config, instance_id=public_id)
                await self._registry.connect_instance(iid)
                logger.info("plugin_instance_connected", instance_id=iid, plugin_id=plugin_id)
            except Exception as exc:
                logger.error("plugin_instance_init_failed", plugin_id=plugin_id, error=str(exc))
                continue

            # 4. Fetch channel mappings for this instance
            try:
                mappings = await self._api.fetch_channel_mappings(public_id)
                for m in mappings:
                    event_pid = m.get("event_public_id")
                    ch_id = m.get("channel_id")
                    if event_pid and ch_id:
                        self._channel_map.add(public_id, ch_id, event_pid)
            except Exception as exc:
                logger.warning("channel_mapping_fetch_failed", instance=public_id, error=str(exc))

        logger.info(
            "plugin_bridge_initialized",
            instances=len(self._registry.list_instances()),
            mappings=len(self._channel_map),
        )
        self._initialized = True

    # ── Sensor loop tick ─────────────────────────────────────────────────

    async def read_and_send(self) -> None:
        """Read all plugin input channels and send mapped values as telemetry."""
        if not self._initialized:
            return

        all_values = await self._registry.read_all_inputs()
        datapoints: list[dict[str, Any]] = []

        for entry in all_values:
            iid = str(entry["instance_id"])
            ch_id = str(entry["channel_id"])
            value = entry["value"]

            event_pid = self._channel_map.event_for(iid, ch_id)
            if event_pid:
                datapoints.append({"value": float(value), "event_public_id": event_pid})  # type: ignore[arg-type]

        if datapoints:
            await self._telemetry.send(datapoints)
            logger.debug("plugin_telemetry_sent", count=len(datapoints))

    # ── Actuator loop tick ───────────────────────────────────────────────

    async def receive_and_write(self) -> None:
        """Fetch latest actuator values from backend and write to plugin outputs."""
        if not self._initialized:
            return

        try:
            latest = await self._api.get("/datapoints/latest")
            if not isinstance(latest, list):
                return

            for dp_data in latest:
                event_pid = dp_data.get("event_public_id", "")
                value = dp_data.get("value")
                if value is None:
                    continue

                target = self._channel_map.channel_for(event_pid)
                if not target:
                    continue

                iid, ch_id = target
                try:
                    await self._registry.write(iid, ch_id, float(value))
                except Exception as exc:
                    logger.warning("plugin_write_failed", instance=iid, channel=ch_id, error=str(exc))

        except Exception as exc:
            logger.warning("plugin_actuator_loop_error", error=str(exc))

    # ── Shutdown ─────────────────────────────────────────────────────────

    async def shutdown(self) -> None:
        """Disconnect all plugin instances (applies safe-state)."""
        if self._initialized:
            await self._registry.disconnect_all()
            logger.info("plugin_bridge_shutdown_complete")
            self._initialized = False
