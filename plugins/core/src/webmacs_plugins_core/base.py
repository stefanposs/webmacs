"""Plugin base classes — the contract every plugin must implement."""

from __future__ import annotations

import asyncio
import math
import random
import time
from abc import ABC, abstractmethod
from typing import ClassVar

import structlog

from webmacs_plugins_core.channels import ChannelDescriptor, ChannelDirection
from webmacs_plugins_core.config import PluginInstanceConfig, PluginMeta
from webmacs_plugins_core.errors import CapabilityNotFoundError, PluginConnectionError, PluginStateError
from webmacs_plugins_core.health import HealthReport
from webmacs_plugins_core.types import ChannelValue, PluginState

logger = structlog.get_logger()


class DevicePlugin(ABC):
    """Async base class for hardware device plugins.

    Lifecycle::

        DevicePlugin()          → state = discovered
        plugin.configure(cfg)   → state = configured
        plugin.connect()        → state = connected
        plugin.read(ch_id)      → reads a channel value
        plugin.write(ch_id, v)  → writes to an actuator
        plugin.disconnect()     → state = disconnected

    Subclass this for async-native protocols (OPC-UA, MQTT).
    For sync/blocking protocols, use ``SyncDevicePlugin`` instead.
    """

    meta: ClassVar[PluginMeta]
    config_schema: ClassVar[type[PluginInstanceConfig]] = PluginInstanceConfig

    def __init__(self) -> None:
        self._state: PluginState = PluginState.discovered
        self._config: PluginInstanceConfig | None = None
        self._channels: dict[str, ChannelDescriptor] = {}
        self._error_count: int = 0
        self._last_error: str | None = None
        self._log = logger.bind(plugin_id=self.meta.id)

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def state(self) -> PluginState:
        return self._state

    @property
    def config(self) -> PluginInstanceConfig | None:
        return self._config

    @property
    def instance_name(self) -> str:
        return self._config.instance_name if self._config else self.meta.name

    @property
    def is_demo_mode(self) -> bool:
        return bool(self._config and self._config.demo_mode)

    @property
    def channels(self) -> dict[str, ChannelDescriptor]:
        return dict(self._channels)

    @property
    def error_count(self) -> int:
        return self._error_count

    @property
    def last_error(self) -> str | None:
        return self._last_error

    # ── Lifecycle ────────────────────────────────────────────────────────

    def configure(self, config: dict[str, object]) -> None:
        """Validate and apply configuration, then discover channels."""
        self._config = self.config_schema(**config)
        channel_list = self.get_channels()
        self._channels = {ch.id: ch for ch in channel_list}
        self._state = PluginState.configured
        self._log.info("plugin_configured", instance=self.instance_name, channels=len(self._channels))

    async def connect(self) -> None:
        """Establish connection to the hardware or protocol."""
        if self._state not in (PluginState.configured, PluginState.disconnected, PluginState.error):
            raise PluginStateError(self.meta.id, self._state, "configured|disconnected|error")
        self._state = PluginState.connecting
        try:
            if not self.is_demo_mode:
                await self._do_connect()
            self._state = PluginState.connected
            self._error_count = 0
            self._last_error = None
            self._log.info("plugin_connected", instance=self.instance_name, demo=self.is_demo_mode)
        except Exception as exc:
            self._state = PluginState.error
            self._error_count += 1
            self._last_error = str(exc)
            self._log.error("plugin_connect_failed", error=str(exc))
            raise PluginConnectionError(self.meta.id, str(exc)) from exc

    async def disconnect(self) -> None:
        """Gracefully disconnect, applying safe-state values to outputs first."""
        self._state = PluginState.disconnecting
        try:
            await self._apply_safe_state()
            if not self.is_demo_mode:
                await self._do_disconnect()
        except Exception as exc:
            self._log.warning("plugin_disconnect_error", error=str(exc))
        finally:
            self._state = PluginState.disconnected
            self._log.info("plugin_disconnected", instance=self.instance_name)

    async def read(self, channel_id: str) -> ChannelValue | None:
        """Read a value from an input channel, applying conversion."""
        ch = self._channels.get(channel_id)
        if not ch:
            raise CapabilityNotFoundError(self.meta.id, channel_id)
        try:
            if self.is_demo_mode:
                raw = self._simulate_read(ch)
            else:
                raw = await self._do_read(channel_id)
            if raw is None:
                return None
            return ch.read_conversion.convert(float(raw))
        except CapabilityNotFoundError:
            raise
        except Exception as exc:
            self._error_count += 1
            self._last_error = str(exc)
            self._log.warning("plugin_read_error", channel=channel_id, error=str(exc))
            return None

    async def write(self, channel_id: str, value: ChannelValue) -> None:
        """Write a value to an output channel, with clamping and conversion."""
        ch = self._channels.get(channel_id)
        if not ch:
            raise CapabilityNotFoundError(self.meta.id, channel_id)
        if ch.direction == ChannelDirection.input:
            raise PluginStateError(self.meta.id, "write", f"Channel '{channel_id}' is read-only")
        # Clamp to safe range before writing
        numeric = float(value)
        clamped = max(ch.min_value, min(ch.max_value, numeric))
        raw = ch.write_conversion.invert(clamped)
        if self.is_demo_mode:
            self._log.debug("demo_write", channel=channel_id, value=clamped)
            return
        try:
            await self._do_write(channel_id, raw)
        except Exception as exc:
            self._error_count += 1
            self._last_error = str(exc)
            self._log.warning("plugin_write_error", channel=channel_id, error=str(exc))
            raise

    async def read_all_inputs(self) -> dict[str, ChannelValue | None]:
        """Read all input channels in one call. Override for batch-optimized protocols."""
        results: dict[str, ChannelValue | None] = {}
        for ch_id, ch in self._channels.items():
            if ch.direction in (ChannelDirection.input, ChannelDirection.bidirectional):
                results[ch_id] = await self.read(ch_id)
        return results

    def health_check(self) -> HealthReport:
        """Return current health status."""
        return HealthReport(
            plugin_id=self.meta.id,
            instance_name=self.instance_name,
            state=self._state,
            error_count=self._error_count,
            last_error=self._last_error,
            channel_count=len(self._channels),
            demo_mode=self.is_demo_mode,
        )

    # ── Context manager ──────────────────────────────────────────────────

    async def __aenter__(self) -> DevicePlugin:
        await self.connect()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.disconnect()

    async def apply_safe_state(self) -> None:
        """Public wrapper — write safe-state values to all outputs that define one."""
        await self._apply_safe_state()

    # ── Abstract methods — implement these in your plugin ────────────────

    @abstractmethod
    def get_channels(self) -> list[ChannelDescriptor]:
        """Return the list of channels this plugin instance provides."""

    @abstractmethod
    async def _do_connect(self) -> None:
        """Open the connection to the hardware. Not called in demo mode."""

    @abstractmethod
    async def _do_disconnect(self) -> None:
        """Close the connection to the hardware. Not called in demo mode."""

    @abstractmethod
    async def _do_read(self, channel_id: str) -> ChannelValue | None:
        """Read a raw value from a hardware channel."""

    @abstractmethod
    async def _do_write(self, channel_id: str, value: ChannelValue) -> None:
        """Write a raw value to a hardware channel."""

    # ── Internal helpers ─────────────────────────────────────────────────

    async def _apply_safe_state(self) -> None:
        """Write safe values to all output channels that define one."""
        for ch_id, ch in self._channels.items():
            if ch.direction != ChannelDirection.input and ch.safe_value is not None:
                try:
                    await self._do_write(ch_id, ch.safe_value)
                    self._log.info("safe_state_applied", channel=ch_id, value=ch.safe_value)
                except Exception as exc:
                    self._log.error("safe_state_failed", channel=ch_id, error=str(exc))

    _sim_start: float = 0.0
    _sim_rng: random.Random | None = None

    def _simulate_read(self, ch: ChannelDescriptor) -> float:
        """Generate a simulated value based on the channel's SimulationSpec."""
        if self._sim_start == 0.0:
            self._sim_start = time.monotonic()
            self._sim_rng = random.Random(hash(self.instance_name))

        rng = self._sim_rng or random.Random()
        t = time.monotonic() - self._sim_start
        sim = ch.simulation
        base = sim.base_value
        amp = sim.amplitude
        period = sim.period_seconds

        match sim.profile:
            case "sine_wave":
                value = base + amp * math.sin(2 * math.pi * t / period)
            case "sawtooth":
                phase = (t % period) / period
                value = base - amp + (2 * amp * phase)
            case "random_walk":
                step = rng.gauss(0, amp * 0.05)
                value = base + step
            case "step":
                cycle = int(t / period) % 2
                value = base + amp if cycle else base - amp
            case "constant":
                value = base
            case _:
                value = base + amp * math.sin(2 * math.pi * t / period)

        if sim.noise > 0:
            value += rng.gauss(0, sim.noise)
        return round(max(ch.min_value, min(ch.max_value, value)), 3)


class SyncDevicePlugin(DevicePlugin):
    """Convenience base for plugins that use synchronous/blocking hardware libraries.

    Wraps ``connect_sync``, ``read_sync``, ``write_sync``, ``disconnect_sync``
    via ``asyncio.to_thread()`` so they run in a thread pool without blocking
    the event loop. A per-instance lock prevents concurrent hardware access.

    Example::

        class MyModbusPlugin(SyncDevicePlugin):
            meta = PluginMeta(id="modbus-tcp", ...)
            config_schema = MyModbusConfig

            def get_channels(self): ...
            def connect_sync(self): ...
            def disconnect_sync(self): ...
            def read_sync(self, channel_id): ...
            def write_sync(self, channel_id, value): ...
    """

    def __init__(self) -> None:
        super().__init__()
        self._hw_lock = asyncio.Lock()

    async def _do_connect(self) -> None:
        await asyncio.to_thread(self.connect_sync)

    async def _do_disconnect(self) -> None:
        await asyncio.to_thread(self.disconnect_sync)

    async def _do_read(self, channel_id: str) -> ChannelValue | None:
        async with self._hw_lock:
            return await asyncio.to_thread(self.read_sync, channel_id)

    async def _do_write(self, channel_id: str, value: ChannelValue) -> None:
        async with self._hw_lock:
            await asyncio.to_thread(self.write_sync, channel_id, value)

    # ── Abstract sync methods — implement these ──────────────────────────

    @abstractmethod
    def connect_sync(self) -> None:
        """Open the hardware connection (runs in a thread)."""

    @abstractmethod
    def disconnect_sync(self) -> None:
        """Close the hardware connection (runs in a thread)."""

    @abstractmethod
    def read_sync(self, channel_id: str) -> ChannelValue | None:
        """Read a raw value from hardware (runs in a thread)."""

    @abstractmethod
    def write_sync(self, channel_id: str, value: ChannelValue) -> None:
        """Write a raw value to hardware (runs in a thread)."""
