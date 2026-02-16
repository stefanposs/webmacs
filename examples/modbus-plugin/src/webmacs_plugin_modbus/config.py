"""Custom configuration for the Modbus sensor plugin.

Subclasses ``PluginInstanceConfig`` to add Modbus-specific fields.
The Pydantic JSON Schema is used by the WebMACS frontend to render
a dynamic configuration form.
"""

from __future__ import annotations

from pydantic import Field

from webmacs_plugins_core.config import PluginInstanceConfig


class ModbusSensorConfig(PluginInstanceConfig):
    """Configuration schema for Modbus TCP connections.

    All fields include validation constraints and descriptions that
    are forwarded to the frontend form renderer.
    """

    host: str = Field(
        default="192.168.1.1",
        min_length=1,
        max_length=255,
        description="Modbus TCP host address (IP or hostname)",
        json_schema_extra={"ui_order": 10},
    )
    port: int = Field(
        default=502,
        ge=1,
        le=65535,
        description="Modbus TCP port",
        json_schema_extra={"ui_order": 11},
    )
    unit_id: int = Field(
        default=1,
        ge=0,
        le=247,
        description="Modbus unit/slave ID",
        json_schema_extra={"ui_order": 12},
    )
    timeout_seconds: float = Field(
        default=3.0,
        ge=0.5,
        le=30.0,
        description="Connection and read timeout in seconds",
        json_schema_extra={"ui_order": 13},
    )
