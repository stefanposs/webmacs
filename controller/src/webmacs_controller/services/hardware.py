"""Hardware abstraction layer for RevolutionPi."""

import math
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import structlog

from webmacs_controller.schemas import EventSchema, EventType

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
            case "humidy1":
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


# ─── Signal Simulation ──────────────────────────────────────────────────────


class SignalType(StrEnum):
    sine_wave = "sine_wave"
    random_walk = "random_walk"
    sawtooth = "sawtooth"
    step_function = "step_function"


@dataclass
class SignalProfile:
    """Defines how a simulated sensor generates values."""

    label: str
    min_value: float
    max_value: float
    signal_type: SignalType = SignalType.sine_wave
    period: float = 60.0
    noise_pct: float = 0.05
    phase_offset: float = 0.0

    def generate(self, t: float) -> float:
        """Generate a value at time *t* seconds since start."""
        amplitude = (self.max_value - self.min_value) / 2
        center = self.min_value + amplitude

        match self.signal_type:
            case SignalType.sine_wave:
                base = center + amplitude * math.sin(2 * math.pi * t / self.period + self.phase_offset)
            case SignalType.sawtooth:
                phase = ((t / self.period) + self.phase_offset / (2 * math.pi)) % 1.0
                base = self.min_value + (self.max_value - self.min_value) * phase
            case SignalType.step_function:
                phase = ((t / self.period) + self.phase_offset / (2 * math.pi)) % 1.0
                base = self.max_value if phase < 0.5 else self.min_value
            case _:
                base = center

        noise = random.gauss(0, amplitude * self.noise_pct) if amplitude > 0 else 0
        return round(max(self.min_value, min(self.max_value, base + noise)), 2)


# Unit string → preferred signal shape
_UNIT_SIGNAL_MAP: dict[str, SignalType] = {
    "°C": SignalType.sine_wave,
    "bar": SignalType.sawtooth,
    "mbar": SignalType.sawtooth,
    "m³/h": SignalType.sine_wave,
    "L/min": SignalType.sine_wave,
    "%": SignalType.sine_wave,
}


class SimulatedHardware(HardwareInterface):
    """Realistic simulated hardware for dev/demo mode.

    Generates plausible sensor data based on event min/max ranges.
    Each sensor gets a deterministic signal profile.
    """

    def __init__(
        self,
        events: list[EventSchema],
        revpi_mapping: dict[str, Any] | None = None,
        seed: int = 42,
    ) -> None:
        self._profiles: dict[str, SignalProfile] = {}
        self._start_time = time.monotonic()
        self._write_store: dict[str, float] = {}
        rng = random.Random(seed)

        for event in events:
            if event.type != EventType.sensor:
                continue

            label = event.public_id
            if revpi_mapping:
                mapping = revpi_mapping.get(event.public_id, {})
                if mapping.get("REVPI"):
                    label = mapping["REVPI"]

            signal_type = _UNIT_SIGNAL_MAP.get(event.unit, SignalType.sine_wave)
            period = rng.uniform(30.0, 120.0)
            phase = rng.uniform(0, 2 * math.pi)

            self._profiles[label] = SignalProfile(
                label=label,
                min_value=event.min_value,
                max_value=event.max_value,
                signal_type=signal_type,
                period=period,
                phase_offset=phase,
            )

        logger.info("SimulatedHardware initialized", sensor_profiles=len(self._profiles))

    def read_value(self, label: str) -> float | None:
        """Generate a realistic value for the given label."""
        profile = self._profiles.get(label)
        if not profile:
            return None
        t = time.monotonic() - self._start_time
        return profile.generate(t)

    def write_value(self, label: str, value: float) -> None:
        """Store value in memory."""
        self._write_store[label] = value
        logger.debug("SimulatedHardware write", label=label, value=value)
