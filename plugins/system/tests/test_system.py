"""Tests for the system monitoring plugin."""

from typing import ClassVar

from webmacs_plugin_system import SystemPlugin
from webmacs_plugins_core.testing import PluginConformanceSuite


class TestSystemPlugin(PluginConformanceSuite):
    """Standard conformance suite (runs in demo mode)."""

    plugin_class = SystemPlugin
    default_config: ClassVar[dict] = {}
