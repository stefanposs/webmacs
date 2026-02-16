"""Weather Station plugin — example custom plugin for WebMACS.

Demonstrates how to build, test, and upload a custom plugin that
integrates a weather sensor station with five input channels:

* Temperature (°C)
* Humidity (%)
* Wind Speed (km/h)
* Barometric Pressure (hPa)
* Rainfall (mm/h)

This serves as a template for plugin authors.  Copy this directory,
rename classes and channels, and adjust the simulation specs or implement
real hardware communication in the ``_do_*`` methods.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from webmacs_plugins_core.base import DevicePlugin
from webmacs_plugins_core.channels import ChannelDescriptor, ChannelDirection, SimulationSpec
from webmacs_plugins_core.config import PluginMeta

if TYPE_CHECKING:
    from webmacs_plugins_core.types import ChannelValue

logger = structlog.get_logger()


class WeatherStationPlugin(DevicePlugin):
    """Reads environmental data from a weather station.

    In **demo mode** (the default), realistic values are simulated using
    the ``SimulationSpec`` on each channel — no hardware required.

    To connect to real hardware, implement the four ``_do_*`` methods
    with your protocol logic (e.g. Modbus, HTTP, serial).
    """

    meta = PluginMeta(
        id="weather",
        name="Weather Station",
        version="0.1.0",
        vendor="Your Company",
        description="Environmental monitoring — temperature, humidity, wind, pressure, and rainfall.",
        protocol="example",
        url="https://github.com/yourorg/webmacs-plugin-weather",
        tags=["weather", "environment", "sensors"],
    )

    # ── Channel declaration ──────────────────────────────────────────────

    def get_channels(self) -> list[ChannelDescriptor]:
        """Declare five input channels for weather telemetry."""
        return [
            ChannelDescriptor(
                id="temperature",
                name="Ambient Temperature",
                direction=ChannelDirection.input,
                unit="°C",
                min_value=-40.0,
                max_value=60.0,
                simulation=SimulationSpec(
                    profile="sine_wave",
                    base_value=22.0,
                    amplitude=8.0,
                    period_seconds=300.0,
                    noise=0.3,
                ),
            ),
            ChannelDescriptor(
                id="humidity",
                name="Relative Humidity",
                direction=ChannelDirection.input,
                unit="%",
                min_value=0.0,
                max_value=100.0,
                simulation=SimulationSpec(
                    profile="sine_wave",
                    base_value=55.0,
                    amplitude=20.0,
                    period_seconds=600.0,
                    noise=1.0,
                ),
            ),
            ChannelDescriptor(
                id="wind_speed",
                name="Wind Speed",
                direction=ChannelDirection.input,
                unit="km/h",
                min_value=0.0,
                max_value=200.0,
                simulation=SimulationSpec(
                    profile="random_walk",
                    base_value=12.0,
                    amplitude=8.0,
                    noise=0.5,
                ),
            ),
            ChannelDescriptor(
                id="pressure",
                name="Barometric Pressure",
                direction=ChannelDirection.input,
                unit="hPa",
                min_value=900.0,
                max_value=1100.0,
                simulation=SimulationSpec(
                    profile="sine_wave",
                    base_value=1013.0,
                    amplitude=15.0,
                    period_seconds=900.0,
                    noise=0.2,
                ),
            ),
            ChannelDescriptor(
                id="rainfall",
                name="Rainfall Rate",
                direction=ChannelDirection.input,
                unit="mm/h",
                min_value=0.0,
                max_value=100.0,
                simulation=SimulationSpec(
                    profile="random_walk",
                    base_value=2.0,
                    amplitude=5.0,
                    noise=0.3,
                ),
            ),
        ]

    # ── Hardware integration ─────────────────────────────────────────────
    #
    # Replace these stubs with real protocol logic for production use.
    # In demo mode the base class handles simulated values automatically,
    # so these are only called when demo_mode=False.

    async def _do_connect(self) -> None:
        """Open connection to the weather station hardware.

        Example implementation for a serial device::

            import serial_asyncio
            self._reader, self._writer = await serial_asyncio.open_serial_connection(
                url=self.config.serial_port, baudrate=9600,
            )
        """
        logger.info("weather_connect", msg="Replace with real connection logic")

    async def _do_disconnect(self) -> None:
        """Close the hardware connection gracefully."""
        logger.info("weather_disconnect", msg="Replace with real disconnection logic")

    async def _do_read(self, channel_id: str) -> ChannelValue | None:
        """Read a single channel value from the hardware.

        Args:
            channel_id: One of ``temperature``, ``humidity``, ``wind_speed``,
                ``pressure``, or ``rainfall``.

        Returns:
            The measured value as a float, or ``None`` if unavailable.
        """
        # In a real implementation you would query the device here.
        logger.warning("weather_read_stub", channel=channel_id)
        return None

    async def _do_write(self, channel_id: str, value: ChannelValue) -> None:
        """Write to a channel — not applicable for a sensor-only station.

        This plugin has no output channels, so this method is never called
        during normal operation.  It is included for contract completeness.
        """
