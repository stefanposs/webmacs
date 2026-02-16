"""Tests for the Revolution Pi plugin."""

from __future__ import annotations

import tempfile
from typing import ClassVar

from webmacs_plugin_revpi import RevPiPlugin
from webmacs_plugins_core.testing import PluginConformanceSuite


class TestRevPiPlugin(PluginConformanceSuite):
    """Standard conformance suite (runs in demo mode → fallback channels)."""

    plugin_class = RevPiPlugin
    default_config: ClassVar[dict] = {}


class TestRevPiPluginUnit:
    """Unit tests for RevPi-specific behaviour."""

    def test_fallback_channels_count(self) -> None:
        """Without piCtory, fallback gives 14 DI + 14 DO = 28."""
        channels = RevPiPlugin._fallback_channels()  # noqa: SLF001
        inputs = [c for c in channels if c.direction.value == "input"]
        outputs = [c for c in channels if c.direction.value == "output"]
        assert len(inputs) == 14
        assert len(outputs) == 14

    def test_max_for_bit_length(self) -> None:
        assert (
            RevPiPlugin._max_for_bit_length(  # noqa: SLF001
                {"bitLength": "1"},
            )
            == 1.0
        )
        assert (
            RevPiPlugin._max_for_bit_length(  # noqa: SLF001
                {"bitLength": "8"},
            )
            == 255.0
        )
        assert (
            RevPiPlugin._max_for_bit_length(  # noqa: SLF001
                {"bitLength": "16"},
            )
            == 65535.0
        )

    def test_unit_for_type(self) -> None:
        assert (
            RevPiPlugin._unit_for_type(  # noqa: SLF001
                {"comment": "Temperature sensor"},
            )
            == "°C"
        )
        assert (
            RevPiPlugin._unit_for_type(  # noqa: SLF001
                {"comment": "Voltage input"},
            )
            == "V"
        )
        assert (
            RevPiPlugin._unit_for_type(  # noqa: SLF001
                {"comment": "something"},
            )
            == "bool"
        )
        assert (
            RevPiPlugin._unit_for_type(  # noqa: SLF001
                {"comment": "something", "bitLength": 16},
            )
            == "raw"
        )

    def test_custom_config_schema(self) -> None:
        """RevPiConfig should accept device_filter and configrsc."""
        from webmacs_plugin_revpi.plugin import RevPiConfig

        tmp = tempfile.gettempdir()
        test_path = f"{tmp}/test.rsc"
        cfg = RevPiConfig(
            instance_name="test-revpi",
            device_filter=["DIO_Module_1"],
            configrsc=test_path,
        )
        assert cfg.device_filter == ["DIO_Module_1"]
        assert cfg.configrsc == test_path
