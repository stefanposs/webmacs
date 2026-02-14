"""Plugin error hierarchy — every exception carries plugin context for debugging."""

from __future__ import annotations


class PluginError(Exception):
    """Base error for all plugin-related failures."""

    def __init__(self, plugin_id: str, message: str) -> None:
        self.plugin_id = plugin_id
        super().__init__(f"[{plugin_id}] {message}")


class PluginLoadError(PluginError):
    """Raised when a plugin class cannot be loaded from an entry point."""


class PluginConfigError(PluginError):
    """Raised when plugin configuration validation fails."""


class PluginConnectionError(PluginError):
    """Raised when connection to the hardware/protocol fails."""


class PluginTimeoutError(PluginError):
    """Raised when a read/write operation exceeds the configured timeout."""


class CapabilityNotFoundError(PluginError):
    """Raised when accessing a channel that doesn't exist on this plugin."""

    def __init__(self, plugin_id: str, channel_id: str) -> None:
        self.channel_id = channel_id
        super().__init__(plugin_id, f"Channel '{channel_id}' not found")


class PluginStateError(PluginError):
    """Raised when an operation is attempted in an invalid lifecycle state."""

    def __init__(self, plugin_id: str, current_state: str, expected: str) -> None:
        self.current_state = current_state
        self.expected = expected
        super().__init__(plugin_id, f"Expected state '{expected}', got '{current_state}'")
