"""Hardware abstraction layer for RevolutionPi.

.. deprecated::
    This module is superseded by the plugin system (``PluginBridge`` +
    ``DevicePlugin``).  It is kept only for backward compatibility and
    will be removed in a future release.  Use ``webmacs_plugins_core``
    channels and conversion specs instead.
"""

from __future__ import annotations

import random
import warnings
from abc import ABC, abstractmethod

import structlog

warnings.warn(
    "webmacs_controller.services.hardware is deprecated — use the plugin system (DevicePlugin + PluginBridge) instead.",
    DeprecationWarning,
    stacklevel=2,
)

logger = structlog.get_logger()


class HardwareInterface(ABC):
    """Abstract hardware interface for testability."""

    @abstractmethod
    def read_value(self, label: str) -> float | None:
        """Read a sensor value from hardware."""

    @abstractmethod
    def write_value(self, label: str, value: float) -> None:
        """Write an actuator value to hardware."""


class RevPiHardware(HardwareInterface):
    """Revolution Pi hardware implementation."""

    def __init__(self) -> None:
        try:
            import revpimodio2

            self._rpi = revpimodio2.RevPiModIO(autorefresh=True)
            logger.info("RevPi hardware initialized")
        except ImportError:
            logger.warning("revpimodio2 not installed, hardware interface unavailable")
            self._rpi = None
        except Exception as e:
            logger.exception("Failed to initialize RevPi hardware", error=str(e))
            self._rpi = None

    def read_value(self, label: str) -> float | None:
        """Read and convert a sensor value from RevPi."""
        if not self._rpi:
            return None

        raw = self._rpi.io[label].value

        match label:
            case "volumeflow1":
                return self._convert_volumeflow(raw)
            case "temp1" | "temp2" | "temp3":
                return float(raw) / 10.0
            case "pressure1" | "pressure2":
                return float(raw) / 1000.0
            case "humidity1":
                return float(raw) / 100.0
            case _:
                return float(raw)

    def write_value(self, label: str, value: float) -> None:
        """Write a converted actuator value to RevPi."""
        if not self._rpi:
            return

        match label:
            case "valve1":
                self._rpi.io[label].value = int(value)
            case "heater1":
                self._rpi.io[label].value = self._celsius_to_ma(value)
            case "blower1":
                self._rpi.io[label].value = int(value * 100)
            case _:
                self._rpi.io[label].value = int(value)

    @staticmethod
    def _celsius_to_ma(celsius: float) -> int:
        """Convert temperature in Celsius to milliamps (4-20mA range)."""
        max_temp, _min_temp = 100.0, 0.0
        max_ma, min_ma = 20000, 4000
        return int(((max_ma - min_ma) / max_temp) * celsius + min_ma)

    @staticmethod
    def _convert_volumeflow(raw: int) -> float:
        """Convert raw DAC value to m³/h volumeflow."""
        raw = abs(raw)
        min_dec, max_dec = 931, 4236
        max_flow = 40.0
        m = max_flow / (max_dec - min_dec)
        d = -m * min_dec
        return round(m * raw + d, 2)


class MockHardware(HardwareInterface):
    """Mock hardware for unit testing - returns random values."""

    def __init__(self) -> None:
        self._values: dict[str, float] = {}
        logger.info("Mock hardware initialized (development mode)")

    def read_value(self, label: str) -> float | None:
        """Return random demo data for sensors."""
        return round(random.uniform(0, 100), 2)

    def write_value(self, label: str, value: float) -> None:
        """Store value in memory."""
        self._values[label] = value
        logger.debug("Mock hardware write", label=label, value=value)
