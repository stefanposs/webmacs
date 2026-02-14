"""Test helpers and conformance suite for plugin authors.

Plugin developers can inherit from ``PluginConformanceSuite`` and
get a battery of tests that validate their plugin contract.

Usage::

    from webmacs_plugins_core.testing import PluginConformanceSuite

    class TestMyPlugin(PluginConformanceSuite):
        plugin_class = MyPlugin
        default_config = {"host": "localhost", "port": 502}
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

import pytest

from webmacs_plugins_core.channels import ChannelDirection
from webmacs_plugins_core.config import PluginMeta
from webmacs_plugins_core.health import HealthReport
from webmacs_plugins_core.types import PluginState

if TYPE_CHECKING:
    from webmacs_plugins_core.base import DevicePlugin


class PluginConformanceSuite:
    """Reusable conformance tests — plugin authors subclass and set two class-vars.

    Subclasses only need to set ``plugin_class`` and ``default_config``;
    all test methods are inherited automatically.
    """

    plugin_class: ClassVar[type[DevicePlugin]]
    default_config: ClassVar[dict[str, object]] = {}

    @pytest.fixture
    def plugin(self) -> DevicePlugin:
        p = self.plugin_class()
        p.configure(self.default_config | {"demo_mode": True})
        return p

    # ── Metadata ─────────────────────────────────────────────────────────

    def test_meta_is_plugin_meta(self) -> None:
        meta = self.plugin_class.meta
        assert isinstance(meta, PluginMeta)

    def test_meta_fields_non_empty(self) -> None:
        meta = self.plugin_class.meta
        assert meta.id, "PluginMeta.id must not be empty"
        assert meta.name, "PluginMeta.name must not be empty"
        assert meta.version, "PluginMeta.version must not be empty"

    def test_meta_id_is_kebab_case(self) -> None:
        meta = self.plugin_class.meta
        assert meta.id == meta.id.lower(), "PluginMeta.id must be lowercase"
        assert " " not in meta.id, "PluginMeta.id must not contain spaces"

    # ── Channels ─────────────────────────────────────────────────────────

    def test_has_at_least_one_channel(self, plugin: DevicePlugin) -> None:
        assert len(plugin.channels) > 0, "Plugin must declare at least one channel"

    def test_channel_directions_are_valid(self, plugin: DevicePlugin) -> None:
        for ch_id, ch in plugin.channels.items():
            assert isinstance(ch.direction, ChannelDirection), (
                f"Channel '{ch_id}' has invalid direction: {ch.direction}"
            )

    def test_channel_ids_unique(self, plugin: DevicePlugin) -> None:
        ids = list(plugin.channels.keys())
        assert len(ids) == len(set(ids)), "Duplicate channel ids detected"

    def test_all_channels_have_unit(self, plugin: DevicePlugin) -> None:
        for ch_id, ch in plugin.channels.items():
            assert ch.unit, f"Channel '{ch_id}' is missing a unit"

    # ── Lifecycle ────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_connect_disconnect_cycle(self, plugin: DevicePlugin) -> None:
        assert plugin.state == PluginState.configured
        await plugin.connect()
        assert plugin.state == PluginState.connected
        await plugin.disconnect()
        assert plugin.state == PluginState.disconnected

    @pytest.mark.asyncio
    async def test_double_disconnect_is_safe(self, plugin: DevicePlugin) -> None:
        await plugin.connect()
        await plugin.disconnect()
        await plugin.disconnect()  # should not raise

    # ── Demo mode ────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_demo_mode_read(self, plugin: DevicePlugin) -> None:
        """In demo mode, all input channels must return non-None values."""
        await plugin.connect()
        try:
            inputs = await plugin.read_all_inputs()
            input_channels = [
                ch_id
                for ch_id, ch in plugin.channels.items()
                if ch.direction in (ChannelDirection.input, ChannelDirection.bidirectional)
            ]
            for ch_id in input_channels:
                assert ch_id in inputs, f"Missing demo value for input '{ch_id}'"
                assert inputs[ch_id] is not None, f"Demo value for '{ch_id}' is None"
        finally:
            await plugin.disconnect()

    @pytest.mark.asyncio
    async def test_demo_mode_write(self, plugin: DevicePlugin) -> None:
        """In demo mode, writing to output channels should not raise."""
        await plugin.connect()
        try:
            for ch_id, ch in plugin.channels.items():
                if ch.direction in (ChannelDirection.output, ChannelDirection.bidirectional):
                    await plugin.write(ch_id, 0)
        finally:
            await plugin.disconnect()

    # ── Safe-state ───────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_safe_state_applies(self, plugin: DevicePlugin) -> None:
        await plugin.connect()
        await plugin.apply_safe_state()
        await plugin.disconnect()

    # ── Health ───────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_health_check(self, plugin: DevicePlugin) -> None:
        await plugin.connect()
        try:
            report = plugin.health_check()
            assert isinstance(report, HealthReport)
            assert report.is_healthy
        finally:
            await plugin.disconnect()
