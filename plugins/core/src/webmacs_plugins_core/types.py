"""Shared types for the plugin SDK."""

from __future__ import annotations

from enum import StrEnum

# A channel value can be a float, int, bool, or string.
ChannelValue = float | int | bool | str


class PluginState(StrEnum):
    """Lifecycle states of a plugin instance."""

    discovered = "discovered"
    configured = "configured"
    connecting = "connecting"
    connected = "connected"
    running = "running"
    disconnecting = "disconnecting"
    disconnected = "disconnected"
    error = "error"
