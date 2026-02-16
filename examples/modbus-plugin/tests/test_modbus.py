"""Tests for the Modbus sensor example plugin."""

from typing import ClassVar

import pytest

from webmacs_plugin_modbus import ModbusSensorPlugin
from webmacs_plugin_modbus.config import ModbusSensorConfig
from webmacs_plugins_core.channels import ChannelDirection
from webmacs_plugins_core.testing import PluginConformanceSuite


class TestModbusSensorPlugin(PluginConformanceSuite):
    """Inherits the full conformance battery — tests lifecycle, channels, etc."""

    plugin_class = ModbusSensorPlugin
    default_config: ClassVar[dict] = {
        "host": "127.0.0.1",
        "port": 502,
        "unit_id": 1,
        "timeout_seconds": 3.0,
    }


class TestModbusConfig:
    """Test custom Modbus configuration model."""

    def test_defaults(self) -> None:
        cfg = ModbusSensorConfig()
        assert cfg.host == "192.168.1.1"
        assert cfg.port == 502
        assert cfg.unit_id == 1
        assert cfg.timeout_seconds == 3.0

    def test_custom_values(self) -> None:
        cfg = ModbusSensorConfig(host="10.0.0.50", port=5020, unit_id=5, timeout_seconds=10.0)
        assert cfg.host == "10.0.0.50"
        assert cfg.port == 5020
        assert cfg.unit_id == 5

    def test_invalid_port_rejected(self) -> None:
        with pytest.raises(Exception):
            ModbusSensorConfig(port=99999)

    def test_invalid_unit_id_rejected(self) -> None:
        with pytest.raises(Exception):
            ModbusSensorConfig(unit_id=300)

    def test_timeout_too_low(self) -> None:
        with pytest.raises(Exception):
            ModbusSensorConfig(timeout_seconds=0.1)

    def test_json_schema_has_custom_fields(self) -> None:
        schema = ModbusSensorConfig.model_json_schema()
        props = schema["properties"]
        assert "host" in props
        assert "port" in props
        assert "unit_id" in props
        assert "timeout_seconds" in props


class TestModbusChannels:
    """Test channel declarations specific to the Modbus plugin."""

    def _make_plugin(self) -> ModbusSensorPlugin:
        p = ModbusSensorPlugin()
        p.configure({"instance_name": "test", "demo_mode": True})
        return p

    def test_has_output_channel(self) -> None:
        plugin = self._make_plugin()
        output_channels = [ch for ch in plugin.channels.values() if ch.direction == ChannelDirection.output]
        assert len(output_channels) == 1
        assert output_channels[0].id == "valve_setpoint"

    def test_has_input_channels(self) -> None:
        plugin = self._make_plugin()
        input_channels = [ch for ch in plugin.channels.values() if ch.direction == ChannelDirection.input]
        assert len(input_channels) == 2
        ids = {ch.id for ch in input_channels}
        assert ids == {"temperature", "flow_rate"}

    def test_temperature_has_conversion(self) -> None:
        plugin = self._make_plugin()
        temp = plugin.channels["temperature"]
        assert temp.read_conversion.type == "divide"
        # Raw 1800 → 180.0°C
        assert temp.read_conversion.convert(1800.0) == 180.0

    def test_valve_conversion_roundtrip(self) -> None:
        plugin = self._make_plugin()
        valve = plugin.channels["valve_setpoint"]
        # read_conversion: Raw 5000 → 50%
        assert valve.read_conversion.convert(5000.0) == 50.0
        # write_conversion invert: 50% → raw 5000
        assert valve.write_conversion.invert(50.0) == 5000.0
