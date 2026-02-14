"""Conformance tests for the simulated plugin."""

from typing import ClassVar

from webmacs_plugin_simulated import SimulatedPlugin
from webmacs_plugins_core.testing import PluginConformanceSuite


class TestSimulatedPlugin(PluginConformanceSuite):
    plugin_class = SimulatedPlugin
    default_config: ClassVar[dict] = {}
