"""Modbus TCP Sensor plugin — example with input/output channels and custom config.

Demonstrates:
- Custom configuration via a Pydantic ``PluginInstanceConfig`` subclass.
- Input channels (sensors) and output channels (actuators).
- ``ConversionSpec`` for raw-to-engineering-unit conversion.
- Proper error handling in ``_do_connect``, ``_do_read``, ``_do_write``.
- Custom health check reporting connection latency.

In **demo mode** (the default), values are simulated automatically.
Replace the ``_do_*`` stubs with real ``pymodbus`` calls for production.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import structlog

from webmacs_plugins_core.base import DevicePlugin
from webmacs_plugins_core.channels import (
    ChannelDescriptor,
    ChannelDirection,
    ConversionSpec,
    SimulationSpec,
)
from webmacs_plugins_core.config import PluginMeta

from webmacs_plugin_modbus.config import ModbusSensorConfig

from webmacs_plugins_core.health import HealthReport

if TYPE_CHECKING:
    from webmacs_plugins_core.types import ChannelValue

logger = structlog.get_logger()


class ModbusSensorPlugin(DevicePlugin):
    """Reads/writes Modbus TCP holding registers.

    Configuration fields (host, port, unit_id, timeout) are defined
    in ``ModbusSensorConfig`` and rendered as a dynamic form in the UI.
    """

    meta = PluginMeta(
        id="modbus_sensor",
        name="Modbus TCP Sensor",
        version="0.1.0",
        vendor="Your Company",
        description="Read process temperature and flow rate, control valve setpoint via Modbus TCP.",
        protocol="modbus-tcp",
        url="https://github.com/yourorg/webmacs-plugin-modbus",
        tags=["modbus", "industrial", "sensor", "actuator"],
    )

    # Use the custom config class so WebMACS renders host/port/unit_id fields
    config_schema = ModbusSensorConfig

    def __init__(self) -> None:
        super().__init__()
        # In a real implementation, store the pymodbus client here
        self._client: object | None = None
        self._last_connect_latency: float = 0.0

    # ── Channel declaration ──────────────────────────────────────────────

    def get_channels(self) -> list[ChannelDescriptor]:
        """Declare two input channels (sensors) and one output channel (actuator)."""
        return [
            ChannelDescriptor(
                id="temperature",
                name="Process Temperature",
                direction=ChannelDirection.input,
                unit="°C",
                min_value=0.0,
                max_value=500.0,
                # Raw Modbus register value is in 0.1°C → divide by 10
                read_conversion=ConversionSpec(type="divide", params={"divisor": 10.0}),
                simulation=SimulationSpec(
                    profile="sine_wave",
                    base_value=180.0,
                    amplitude=30.0,
                    period_seconds=120.0,
                    noise=0.5,
                ),
            ),
            ChannelDescriptor(
                id="flow_rate",
                name="Flow Rate",
                direction=ChannelDirection.input,
                unit="L/min",
                min_value=0.0,
                max_value=100.0,
                # Raw register is in 0.01 L/min → linear scale
                read_conversion=ConversionSpec(type="linear", params={"scale": 0.01, "offset": 0.0}),
                simulation=SimulationSpec(
                    profile="random_walk",
                    base_value=45.0,
                    amplitude=10.0,
                    noise=0.3,
                ),
            ),
            ChannelDescriptor(
                id="valve_setpoint",
                name="Valve Setpoint",
                direction=ChannelDirection.output,
                unit="%",
                min_value=0.0,
                max_value=100.0,
                # Raw register: 0–10000 → 0–100%
                read_conversion=ConversionSpec(type="linear", params={"scale": 0.01, "offset": 0.0}),
                write_conversion=ConversionSpec(type="linear", params={"scale": 0.01, "offset": 0.0}),
                simulation=SimulationSpec(
                    profile="sine_wave",
                    base_value=50.0,
                    amplitude=20.0,
                    period_seconds=60.0,
                    noise=0.0,
                ),
            ),
        ]

    # ── Hardware integration ─────────────────────────────────────────────
    #
    # These stubs log warnings. Replace with real pymodbus calls:
    #
    #   from pymodbus.client import AsyncModbusTcpClient
    #
    # See the README for a step-by-step guide.

    async def _do_connect(self) -> None:
        """Open a Modbus TCP connection.

        Example with pymodbus::

            from pymodbus.client import AsyncModbusTcpClient

            cfg = ModbusSensorConfig.model_validate(self.config)
            self._client = AsyncModbusTcpClient(
                host=cfg.host, port=cfg.port, timeout=cfg.timeout_seconds,
            )
            start = time.monotonic()
            connected = await self._client.connect()
            self._last_connect_latency = time.monotonic() - start
            if not connected:
                raise ConnectionError(f"Cannot reach {cfg.host}:{cfg.port}")
        """
        cfg = self._parse_config()
        start = time.monotonic()
        # Simulated connection delay
        self._last_connect_latency = time.monotonic() - start
        logger.info(
            "modbus_connect",
            host=cfg.host,
            port=cfg.port,
            unit_id=cfg.unit_id,
            msg="Replace with real pymodbus connection",
        )

    async def _do_disconnect(self) -> None:
        """Close the Modbus TCP connection.

        Example::

            if self._client:
                self._client.close()
                self._client = None
        """
        self._client = None
        logger.info("modbus_disconnect", msg="Replace with real disconnection logic")

    async def _do_read(self, channel_id: str) -> ChannelValue | None:
        """Read a holding register from the Modbus device.

        Example::

            REGISTER_MAP = {"temperature": 100, "flow_rate": 102}
            address = REGISTER_MAP.get(channel_id)
            if address is None:
                return None

            cfg = ModbusSensorConfig.model_validate(self.config)
            result = await self._client.read_holding_registers(
                address, count=1, slave=cfg.unit_id,
            )
            if result.isError():
                raise IOError(f"Modbus read error: {result}")
            return float(result.registers[0])  # raw value — conversion applied by base
        """
        logger.warning("modbus_read_stub", channel=channel_id)
        return None

    async def _do_write(self, channel_id: str, value: ChannelValue) -> None:
        """Write a holding register on the Modbus device.

        Example::

            REGISTER_MAP = {"valve_setpoint": 200}
            address = REGISTER_MAP.get(channel_id)
            if address is None:
                return

            cfg = ModbusSensorConfig.model_validate(self.config)
            # The base class already clamps the value to min/max.
            # ConversionSpec.invert() converts engineering units back to raw.
            raw = int(round(value))
            result = await self._client.write_register(
                address, raw, slave=cfg.unit_id,
            )
            if result.isError():
                raise IOError(f"Modbus write error: {result}")
        """
        logger.warning("modbus_write_stub", channel=channel_id, value=value)

    # ── Health check ─────────────────────────────────────────────────────

    def health_check(self) -> HealthReport:
        """Report connection health including latency."""
        return super().health_check()

    # ── Helpers ──────────────────────────────────────────────────────────

    def _parse_config(self) -> ModbusSensorConfig:
        """Parse instance config dict into the typed config model."""
        raw = self.config if isinstance(self.config, dict) else {}
        return ModbusSensorConfig.model_validate(raw)
