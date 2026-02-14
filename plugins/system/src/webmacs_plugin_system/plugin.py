"""System monitoring plugin — reads CPU, memory, disk and temperature data.

Works on any Linux/macOS host via *psutil*. Provides read-only input channels
for the most common health metrics of the WebMACS controller host.

Uses the async ``DevicePlugin`` base class because *psutil* calls are
non-blocking (they read from ``/proc`` / sysctl instantly).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

import psutil

from webmacs_plugins_core.base import DevicePlugin
from webmacs_plugins_core.channels import (
    ChannelDescriptor,
    ChannelDirection,
    SimulationSpec,
)
from webmacs_plugins_core.config import PluginMeta

if TYPE_CHECKING:
    from collections.abc import Callable

    from webmacs_plugins_core.types import ChannelValue


class SystemPlugin(DevicePlugin):
    """Reads live system metrics — CPU, memory, disk usage and temperature.

    All channels are **input-only** (read-only).  No hardware connection is
    required — ``psutil`` reads directly from the operating system.

    In *demo mode* the base-class simulation engine generates realistic
    synthetic values, making this plugin useful for UI development as well.
    """

    meta: ClassVar[PluginMeta] = PluginMeta(
        id="system",
        name="System Monitor",
        version="0.1.0",
        vendor="WebMACS",
        description=("CPU, memory, disk and temperature monitoring of the host system."),
        url="https://github.com/stefanposs/webmacs",
        tags=["monitoring", "system", "builtin"],
    )

    # ── Channel declaration ──────────────────────────────────────────────

    def get_channels(self) -> list[ChannelDescriptor]:
        """Return system-health channels."""
        channels: list[ChannelDescriptor] = [
            ChannelDescriptor(
                id="cpu_percent",
                name="CPU Usage",
                direction=ChannelDirection.input,
                unit="%",
                min_value=0.0,
                max_value=100.0,
                simulation=SimulationSpec(
                    profile="sine_wave",
                    base_value=35.0,
                    amplitude=25.0,
                    period_seconds=60.0,
                    noise=3.0,
                ),
            ),
            ChannelDescriptor(
                id="memory_percent",
                name="Memory Usage",
                direction=ChannelDirection.input,
                unit="%",
                min_value=0.0,
                max_value=100.0,
                simulation=SimulationSpec(
                    profile="random_walk",
                    base_value=55.0,
                    amplitude=10.0,
                    noise=1.0,
                ),
            ),
            ChannelDescriptor(
                id="memory_used_gb",
                name="Memory Used",
                direction=ChannelDirection.input,
                unit="GB",
                min_value=0.0,
                max_value=128.0,
                simulation=SimulationSpec(
                    profile="random_walk",
                    base_value=4.0,
                    amplitude=1.5,
                    noise=0.1,
                ),
            ),
            ChannelDescriptor(
                id="disk_percent",
                name="Disk Usage",
                direction=ChannelDirection.input,
                unit="%",
                min_value=0.0,
                max_value=100.0,
                simulation=SimulationSpec(
                    profile="constant",
                    base_value=42.0,
                    amplitude=0.0,
                    noise=0.1,
                ),
            ),
            ChannelDescriptor(
                id="disk_used_gb",
                name="Disk Used",
                direction=ChannelDirection.input,
                unit="GB",
                min_value=0.0,
                max_value=10000.0,
                simulation=SimulationSpec(
                    profile="constant",
                    base_value=120.0,
                    amplitude=0.0,
                    noise=0.5,
                ),
            ),
            ChannelDescriptor(
                id="load_avg_1m",
                name="Load Average (1 min)",
                direction=ChannelDirection.input,
                unit="load",
                min_value=0.0,
                max_value=256.0,
                simulation=SimulationSpec(
                    profile="random_walk",
                    base_value=1.2,
                    amplitude=0.8,
                    noise=0.1,
                ),
            ),
        ]

        channels.append(
            ChannelDescriptor(
                id="cpu_temp",
                name="CPU Temperature",
                direction=ChannelDirection.input,
                unit="°C",
                min_value=0.0,
                max_value=110.0,
                simulation=SimulationSpec(
                    profile="sine_wave",
                    base_value=55.0,
                    amplitude=10.0,
                    period_seconds=120.0,
                    noise=0.5,
                ),
            ),
        )

        return channels

    # ── DevicePlugin async interface ─────────────────────────────────────

    async def _do_connect(self) -> None:
        """Trigger an initial CPU-percent measurement (primes the delta)."""
        psutil.cpu_percent(interval=None)

    async def _do_disconnect(self) -> None:
        """Nothing to clean up."""

    async def _do_read(self, channel_id: str) -> ChannelValue | None:
        """Read the requested system metric.

        Every reader is wrapped in a ``try … except`` so that missing
        sensors, restricted container environments or unsupported OS
        calls never crash the plugin — they simply return ``None``.
        """
        readers: dict[str, Callable[[], ChannelValue | None]] = {
            "cpu_percent": lambda: psutil.cpu_percent(interval=None),
            "cpu_temp": self._read_cpu_temp,
            "memory_percent": lambda: psutil.virtual_memory().percent,
            "memory_used_gb": lambda: round(
                psutil.virtual_memory().used / (1024**3),
                2,
            ),
            "disk_percent": self._read_disk_percent,
            "disk_used_gb": self._read_disk_used_gb,
            "load_avg_1m": self._read_load_avg,
        }
        reader = readers.get(channel_id)
        if reader is None:
            return None
        try:
            return reader()
        except Exception:
            return None

    async def _do_write(
        self,
        channel_id: str,
        value: ChannelValue,
    ) -> None:
        """No writable channels — system metrics are read-only."""

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _read_cpu_temp() -> float | None:
        """Read the primary CPU temperature sensor.

        Returns ``None`` when the OS or environment does not expose
        thermal sensors (macOS, Windows, restricted Docker containers).
        """
        try:
            temps = psutil.sensors_temperatures()
        except (AttributeError, OSError):
            # macOS / Windows: psutil has no sensors_temperatures()
            return None

        if not temps:
            return None

        for name in (
            "coretemp",
            "cpu_thermal",
            "cpu-thermal",
            "soc_thermal",
            "k10temp",
            "zenpower",
        ):
            entries = temps.get(name)
            if entries:
                return entries[0].current

        # Fallback: return the first sensor found
        for entries in temps.values():
            if entries:
                return entries[0].current

        return None

    @staticmethod
    def _read_disk_percent() -> float | None:
        """Read disk usage percent with fallback mount points."""
        for path in ("/", "C:\\"):
            try:
                return psutil.disk_usage(path).percent
            except (OSError, FileNotFoundError):
                continue
        return None

    @staticmethod
    def _read_disk_used_gb() -> float | None:
        """Read disk used in GB with fallback mount points."""
        for path in ("/", "C:\\"):
            try:
                return round(psutil.disk_usage(path).used / (1024**3), 2)
            except (OSError, FileNotFoundError):
                continue
        return None

    @staticmethod
    def _read_load_avg() -> float | None:
        """Read 1-minute load average.

        Falls back to CPU percent on Windows where ``getloadavg()``
        is not available.
        """
        try:
            return psutil.getloadavg()[0]
        except (AttributeError, OSError):
            # Windows: getloadavg() not available — use CPU% as proxy
            try:
                return round(psutil.cpu_percent(interval=None) / 100.0 * psutil.cpu_count(), 2)
            except Exception:
                return None
