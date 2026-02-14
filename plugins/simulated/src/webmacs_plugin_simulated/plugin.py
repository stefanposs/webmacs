"""Simulated device plugin implementation.

Provides nine channels matching a typical fluidised-bed experiment setup
(3 temperatures, 2 pressures, volume flow, humidity, heater, valve) with
configurable signal profiles for demo and testing purposes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from webmacs_plugins_core.base import DevicePlugin
from webmacs_plugins_core.channels import ChannelDescriptor, ChannelDirection, SimulationSpec
from webmacs_plugins_core.config import PluginMeta

if TYPE_CHECKING:
    from webmacs_plugins_core.types import ChannelValue


class SimulatedPlugin(DevicePlugin):
    """Generates realistic simulated sensor/actuator data.

    This plugin is always in demo mode — it never touches real hardware.
    It serves as both a demo tool and a reference implementation for plugin authors.
    """

    meta = PluginMeta(
        id="simulated",
        name="Simulated Device",
        version="0.2.0",
        vendor="WebMACS",
        description="Virtual sensors & actuators for testing and demonstration.",
        url="https://github.com/stefanposs/webmacs",
    )

    # ── Channel declaration ──────────────────────────────────────────────

    def get_channels(self) -> list[ChannelDescriptor]:
        """Return nine demo channels matching a fluidised-bed lab setup."""
        return [
            # ── Temperature sensors ──────────────────────────────────
            ChannelDescriptor(
                id="temp_reactor",
                name="Temperature Reactor",
                direction=ChannelDirection.input,
                unit="°C",
                min_value=20.0,
                max_value=500.0,
                simulation=SimulationSpec(
                    profile="sine_wave",
                    base_value=260.0,
                    amplitude=120.0,
                    period_seconds=120.0,
                    noise=0.5,
                ),
            ),
            ChannelDescriptor(
                id="temp_inlet",
                name="Temperature Inlet",
                direction=ChannelDirection.input,
                unit="°C",
                min_value=15.0,
                max_value=200.0,
                simulation=SimulationSpec(
                    profile="sine_wave",
                    base_value=100.0,
                    amplitude=40.0,
                    period_seconds=90.0,
                    noise=0.3,
                ),
            ),
            ChannelDescriptor(
                id="temp_outlet",
                name="Temperature Outlet",
                direction=ChannelDirection.input,
                unit="°C",
                min_value=15.0,
                max_value=300.0,
                simulation=SimulationSpec(
                    profile="sine_wave",
                    base_value=150.0,
                    amplitude=60.0,
                    period_seconds=100.0,
                    noise=0.4,
                ),
            ),
            # ── Pressure sensors ─────────────────────────────────────
            ChannelDescriptor(
                id="pressure_chamber",
                name="Pressure Chamber",
                direction=ChannelDirection.input,
                unit="bar",
                min_value=0.0,
                max_value=6.0,
                simulation=SimulationSpec(
                    profile="random_walk",
                    base_value=3.0,
                    amplitude=1.5,
                    noise=0.2,
                ),
            ),
            ChannelDescriptor(
                id="pressure_diff",
                name="Pressure Differential",
                direction=ChannelDirection.input,
                unit="mbar",
                min_value=0.0,
                max_value=100.0,
                simulation=SimulationSpec(
                    profile="random_walk",
                    base_value=50.0,
                    amplitude=20.0,
                    noise=0.5,
                ),
            ),
            # ── Flow & humidity ──────────────────────────────────────
            ChannelDescriptor(
                id="volume_flow",
                name="Volume Flow",
                direction=ChannelDirection.input,
                unit="m³/h",
                min_value=0.0,
                max_value=40.0,
                simulation=SimulationSpec(
                    profile="sawtooth",
                    base_value=20.0,
                    amplitude=12.0,
                    period_seconds=60.0,
                    noise=0.8,
                ),
            ),
            ChannelDescriptor(
                id="humidity",
                name="Humidity",
                direction=ChannelDirection.input,
                unit="%",
                min_value=0.0,
                max_value=100.0,
                simulation=SimulationSpec(
                    profile="sine_wave",
                    base_value=55.0,
                    amplitude=15.0,
                    period_seconds=300.0,
                    noise=1.0,
                ),
            ),
            # ── Actuators ────────────────────────────────────────────
            ChannelDescriptor(
                id="heater_power",
                name="Heater Power",
                direction=ChannelDirection.output,
                unit="%",
                min_value=0.0,
                max_value=100.0,
                safe_value=0.0,
            ),
            ChannelDescriptor(
                id="valve_position",
                name="Valve Position",
                direction=ChannelDirection.output,
                unit="%",
                min_value=0.0,
                max_value=100.0,
                safe_value=0.0,
            ),
        ]

    # ── Configuration ────────────────────────────────────────────────────

    def configure(self, config: dict[str, object]) -> None:
        """Configure the simulated plugin — always forces demo_mode=True."""
        config["demo_mode"] = True
        super().configure(config)

    # ── Hardware stubs (never called — always in demo mode) ──────────────

    async def _do_connect(self) -> None:
        pass  # pragma: no cover

    async def _do_disconnect(self) -> None:
        pass  # pragma: no cover

    async def _do_read(self, channel_id: str) -> ChannelValue | None:
        return None  # pragma: no cover

    async def _do_write(self, channel_id: str, value: ChannelValue) -> None:
        pass  # pragma: no cover
