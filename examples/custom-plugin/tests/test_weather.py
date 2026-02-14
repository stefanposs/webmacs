"""Conformance tests for the Weather Station example plugin."""

from typing import ClassVar

from webmacs_plugin_weather import WeatherStationPlugin
from webmacs_plugins_core.testing import PluginConformanceSuite


class TestWeatherStationPlugin(PluginConformanceSuite):
    """Inherits the full conformance battery — no custom tests needed.

    If you add plugin-specific behaviour, add extra test methods here.
    """

    plugin_class = WeatherStationPlugin
    default_config: ClassVar[dict] = {}
