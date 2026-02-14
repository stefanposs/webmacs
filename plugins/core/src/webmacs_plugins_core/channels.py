"""Channel descriptors — declarative hardware channel definitions with conversion and simulation."""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ChannelDirection(StrEnum):
    """Whether a channel reads data (sensor), writes data (actuator), or both."""

    input = "input"
    output = "output"
    bidirectional = "bidirectional"


class ConversionSpec(BaseModel):
    """Declarative value conversion between raw hardware values and engineering units.

    Replaces the old hardcoded ``match label:`` branches with a data-driven approach.
    Each conversion type maps to a pure function — easy to test, easy to extend.
    """

    type: str = Field(default="none", description="Conversion function name")
    params: dict[str, float] = Field(default_factory=dict, description="Parameters for the conversion function")

    def convert(self, raw: float) -> float:
        """Convert a raw hardware value to an engineering value."""
        return _CONVERTERS.get(self.type, _identity)(raw, self.params)

    def invert(self, engineering: float) -> float:
        """Convert an engineering value back to a raw hardware value."""
        return _INVERTERS.get(self.type, _identity)(engineering, self.params)


def _identity(value: float, _params: dict[str, float]) -> float:
    return value


def _linear(raw: float, params: dict[str, float]) -> float:
    """raw * scale + offset"""
    return raw * params.get("scale", 1.0) + params.get("offset", 0.0)


def _linear_inv(eng: float, params: dict[str, float]) -> float:
    scale = params.get("scale", 1.0)
    return (eng - params.get("offset", 0.0)) / scale if scale != 0 else 0.0


def _divide(raw: float, params: dict[str, float]) -> float:
    """raw / divisor — e.g. raw_temp / 10.0 → °C"""
    divisor = params.get("divisor", 1.0)
    return raw / divisor if divisor != 0 else 0.0


def _divide_inv(eng: float, params: dict[str, float]) -> float:
    return eng * params.get("divisor", 1.0)


def _clamp(raw: float, params: dict[str, float]) -> float:
    """Clamp value between min and max."""
    return max(params.get("min", -math.inf), min(params.get("max", math.inf), raw))


# ── Converter registries — extensible via register_conversion() ──────────

_CONVERTERS: dict[str, Any] = {
    "none": _identity,
    "linear": _linear,
    "divide": _divide,
    "clamp": _clamp,
}

_INVERTERS: dict[str, Any] = {
    "none": _identity,
    "linear": _linear_inv,
    "divide": _divide_inv,
    "clamp": _identity,
}


def register_conversion(
    name: str,
    forward: Any,
    inverse: Any | None = None,
) -> None:
    """Register a custom conversion function pair.

    This allows plugin authors to add domain-specific conversions
    (e.g. ``celsius_to_ma``, ``volumeflow_dac``) without modifying the core.
    """
    _CONVERTERS[name] = forward
    _INVERTERS[name] = inverse or _identity


class SimulationSpec(BaseModel):
    """Per-channel simulation parameters for demo mode."""

    profile: str = Field(
        default="sine_wave",
        description="Signal generator: sine_wave, sawtooth, random_walk, step, constant",
    )
    base_value: float = Field(default=0.0, description="Center value around which the signal oscillates")
    amplitude: float = Field(default=1.0, ge=0.0, description="Amplitude of the signal oscillation")
    period_seconds: float = Field(default=60.0, ge=1.0, description="Signal period in seconds")
    noise: float = Field(default=0.0, ge=0.0, description="Gaussian noise standard deviation (absolute)")


class ChannelDescriptor(BaseModel):
    """Describes one I/O channel of a plugin instance.

    This is the core data structure that replaces hardcoded sensor/actuator lists.
    Plugins return a list of these from ``get_channels()``.
    """

    id: str = Field(description="Unique channel identifier within the plugin instance")
    name: str = Field(description="Human-readable display name")
    direction: ChannelDirection = Field(description="Input (sensor), output (actuator), or both")
    data_type: str = Field(default="float", description="Value type: float, int, bool")
    unit: str = Field(default="", description="Engineering unit (°C, bar, %, m³/h, …)")
    min_value: float = Field(default=0.0, description="Minimum engineering value")
    max_value: float = Field(default=100.0, description="Maximum engineering value")
    read_conversion: ConversionSpec = Field(default_factory=ConversionSpec, description="Raw → engineering conversion")
    write_conversion: ConversionSpec = Field(default_factory=ConversionSpec, description="Engineering → raw conversion")
    simulation: SimulationSpec = Field(default_factory=SimulationSpec, description="Demo mode simulation config")
    safe_value: float | None = Field(default=None, description="Value written to output on disconnect/error (safety)")
    ui_hints: dict[str, str] = Field(
        default_factory=dict,
        description="Frontend rendering hints (icon, color, widget_type)",
    )
