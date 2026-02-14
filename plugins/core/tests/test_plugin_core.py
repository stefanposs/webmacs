"""Tests for the webmacs-plugins-core SDK."""

from __future__ import annotations

import pytest

from webmacs_plugins_core.base import DevicePlugin
from webmacs_plugins_core.channels import (
    ChannelDescriptor,
    ChannelDirection,
    ConversionSpec,
    SimulationSpec,
)
from webmacs_plugins_core.config import PluginMeta, RetryPolicy
from webmacs_plugins_core.errors import (
    PluginConfigError,
    PluginConnectionError,
    PluginError,
    PluginLoadError,
)
from webmacs_plugins_core.health import HealthReport
from webmacs_plugins_core.registry import PluginRegistry
from webmacs_plugins_core.types import ChannelValue, PluginState

# ── Test fixtures ────────────────────────────────────────────────────────────


class _TestPlugin(DevicePlugin):
    """Minimal plugin implementation for testing."""

    meta = PluginMeta(
        id="test-plugin",
        name="Test Plugin",
        version="0.1.0",
        vendor="Test",
        description="A plugin for testing the SDK.",
    )

    def __init__(self) -> None:
        super().__init__()
        self._values: dict[str, ChannelValue] = {"sensor1": 42.0}

    def get_channels(self) -> list[ChannelDescriptor]:
        return [
            ChannelDescriptor(
                id="sensor1",
                name="Sensor 1",
                direction=ChannelDirection.input,
                unit="°C",
                min_value=0.0,
                max_value=100.0,
                simulation=SimulationSpec(profile="sine_wave", base_value=50.0, amplitude=10.0),
            ),
            ChannelDescriptor(
                id="actuator1",
                name="Actuator 1",
                direction=ChannelDirection.output,
                unit="%",
                min_value=0.0,
                max_value=100.0,
                safe_value=0.0,
            ),
        ]

    async def _do_connect(self) -> None:
        pass

    async def _do_disconnect(self) -> None:
        pass

    async def _do_read(self, channel_id: str) -> ChannelValue | None:
        return self._values.get(channel_id)

    async def _do_write(self, channel_id: str, value: ChannelValue) -> None:
        self._values[channel_id] = value


# ── PluginMeta tests ─────────────────────────────────────────────────────────


class TestPluginMeta:
    def test_basic_creation(self) -> None:
        meta = PluginMeta(id="test", name="Test", version="1.0.0", vendor="V", description="D")
        assert meta.id == "test"
        assert meta.name == "Test"

    def test_url_default_empty(self) -> None:
        meta = PluginMeta(id="a", name="A", version="1", vendor="V", description="D")
        assert meta.url == ""

    def test_to_dict_includes_url(self) -> None:
        meta = PluginMeta(id="a", name="A", version="1", url="https://example.com")
        d = meta.to_dict()
        assert d["url"] == "https://example.com"


# ── Error hierarchy tests ────────────────────────────────────────────────────


class TestErrors:
    def test_plugin_error_is_exception(self) -> None:
        assert issubclass(PluginError, Exception)

    def test_load_error(self) -> None:
        err = PluginLoadError("myplug", "not found")
        assert "myplug" in str(err)

    def test_config_error(self) -> None:
        err = PluginConfigError("myplug", "bad config")
        assert "myplug" in str(err)

    def test_connection_error(self) -> None:
        err = PluginConnectionError("myplug", "timeout")
        assert "myplug" in str(err)


# ── Channel tests ────────────────────────────────────────────────────────────


class TestChannels:
    def test_channel_descriptor(self) -> None:
        ch = ChannelDescriptor(id="ch1", name="Ch1", direction=ChannelDirection.input, unit="V")
        assert ch.id == "ch1"
        assert ch.direction == ChannelDirection.input

    def test_simulation_spec_defaults(self) -> None:
        spec = SimulationSpec(profile="sine_wave")
        assert spec.base_value == 0.0
        assert spec.period_seconds == 60.0

    def test_conversion_spec(self) -> None:
        conv = ConversionSpec(type="linear", params={"scale": 2.0, "offset": 10.0})
        assert conv.type == "linear"
        assert conv.convert(5.0) == 20.0  # 5 * 2 + 10


# ── DevicePlugin lifecycle tests ─────────────────────────────────────────────


@pytest.mark.asyncio
class TestDevicePlugin:
    async def test_lifecycle(self) -> None:
        p = _TestPlugin()
        assert p.state == PluginState.discovered

        p.configure({"demo_mode": True})
        assert p.state == PluginState.configured

        await p.connect()
        assert p.state == PluginState.connected

        val = await p.read("sensor1")
        assert val is not None  # demo mode uses _simulate_read

        await p.disconnect()
        assert p.state == PluginState.disconnected

    async def test_read_all_inputs(self) -> None:
        p = _TestPlugin()
        p.configure({"demo_mode": True})
        await p.connect()
        inputs = await p.read_all_inputs()
        assert "sensor1" in inputs
        assert inputs["sensor1"] is not None

    async def test_channels_declared(self) -> None:
        p = _TestPlugin()
        p.configure({})
        assert "sensor1" in p.channels
        assert "actuator1" in p.channels

    async def test_write_clamps_to_range(self) -> None:
        p = _TestPlugin()
        p.configure({"demo_mode": False})
        await p.connect()
        # Writing 150 to actuator1 (max=100) should clamp to 100
        await p.write("actuator1", 150.0)
        written = await p.read("actuator1")
        assert written == 100.0
        await p.disconnect()

    async def test_health_check_returns_report(self) -> None:
        p = _TestPlugin()
        p.configure({"demo_mode": True})
        await p.connect()
        report = p.health_check()
        assert isinstance(report, HealthReport)
        assert report.is_healthy
        await p.disconnect()

    async def test_apply_safe_state(self) -> None:
        p = _TestPlugin()
        p.configure({"demo_mode": False})
        await p.connect()
        await p.write("actuator1", 50.0)  # set a non-safe value first
        await p.apply_safe_state()
        # actuator1 has safe_value=0.0 — should have been written
        written = await p.read("actuator1")
        assert written == 0.0
        await p.disconnect()


# ── RetryPolicy tests ───────────────────────────────────────────────────────


class TestRetryPolicy:
    def test_defaults(self) -> None:
        r = RetryPolicy()
        assert r.max_attempts == 5
        assert r.backoff_factor == 2.0

    def test_custom(self) -> None:
        r = RetryPolicy(max_attempts=10, base_delay=2.0, backoff_factor=3.0, max_delay=120.0)
        assert r.max_attempts == 10


# ── PluginRegistry tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestPluginRegistry:
    async def test_register_and_list(self) -> None:
        reg = PluginRegistry()
        reg.register_plugin_class(_TestPlugin)
        available = reg.get_available_plugins()
        assert len(available) == 1
        assert available[0].id == "test-plugin"

    async def test_create_instance(self) -> None:
        reg = PluginRegistry()
        reg.register_plugin_class(_TestPlugin)
        iid = reg.create_instance("test-plugin", {"demo_mode": True}, instance_id="inst-1")
        assert iid == "inst-1"
        assert reg.get_instance("inst-1") is not None

    async def test_connect_and_read(self) -> None:
        reg = PluginRegistry()
        reg.register_plugin_class(_TestPlugin)
        iid = reg.create_instance("test-plugin", {"demo_mode": False}, instance_id="inst-1")
        await reg.connect_instance(iid)
        val = await reg.read(iid, "sensor1")
        assert val == 42.0

    async def test_read_all_inputs(self) -> None:
        reg = PluginRegistry()
        reg.register_plugin_class(_TestPlugin)
        iid = reg.create_instance("test-plugin", {"demo_mode": True}, instance_id="inst-1")
        await reg.connect_instance(iid)
        results = await reg.read_all_inputs()
        assert len(results) == 1
        assert results[0]["channel_id"] == "sensor1"

    async def test_remove_instance(self) -> None:
        reg = PluginRegistry()
        reg.register_plugin_class(_TestPlugin)
        iid = reg.create_instance("test-plugin", {}, instance_id="inst-1")
        assert reg.remove_instance(iid)
        assert reg.get_instance(iid) is None

    async def test_create_unknown_plugin_raises(self) -> None:
        reg = PluginRegistry()
        with pytest.raises(PluginLoadError, match="unknown-plugin"):
            reg.create_instance("unknown-plugin", {})

    async def test_health_reports(self) -> None:
        reg = PluginRegistry()
        reg.register_plugin_class(_TestPlugin)
        reg.create_instance("test-plugin", {"demo_mode": True}, instance_id="inst-1")
        reports = reg.get_health_reports()
        assert isinstance(reports, list)
