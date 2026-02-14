"""WebMACS Plugin SDK — types, base classes, registry, and testing tools."""

from webmacs_plugins_core.base import DevicePlugin, SyncDevicePlugin
from webmacs_plugins_core.channels import ChannelDescriptor, ChannelDirection, ConversionSpec, SimulationSpec
from webmacs_plugins_core.config import PluginInstanceConfig, PluginMeta, RetryPolicy
from webmacs_plugins_core.discovery import discover_plugins
from webmacs_plugins_core.errors import (
    CapabilityNotFoundError,
    PluginConfigError,
    PluginConnectionError,
    PluginError,
    PluginLoadError,
    PluginStateError,
    PluginTimeoutError,
)
from webmacs_plugins_core.health import HealthMonitor, HealthReport
from webmacs_plugins_core.registry import PluginRegistry
from webmacs_plugins_core.types import ChannelValue, PluginState

__all__ = [
    "CapabilityNotFoundError",
    "ChannelDescriptor",
    "ChannelDirection",
    "ChannelValue",
    "ConversionSpec",
    "DevicePlugin",
    "HealthMonitor",
    "HealthReport",
    "PluginConfigError",
    "PluginConnectionError",
    "PluginError",
    "PluginInstanceConfig",
    "PluginLoadError",
    "PluginMeta",
    "PluginRegistry",
    "PluginState",
    "PluginStateError",
    "PluginTimeoutError",
    "RetryPolicy",
    "SimulationSpec",
    "SyncDevicePlugin",
    "discover_plugins",
]

__version__ = "1.0.0"
