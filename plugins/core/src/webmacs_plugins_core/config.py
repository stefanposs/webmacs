"""Plugin configuration models — Pydantic schemas that drive dynamic frontend forms."""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field


class RetryPolicy(BaseModel):
    """Configures automatic reconnection on failure."""

    max_attempts: int = Field(default=5, ge=0, description="Maximum reconnection attempts (0 = infinite)")
    base_delay: float = Field(default=1.0, ge=0.1, description="Initial delay between retries in seconds")
    max_delay: float = Field(default=60.0, ge=1.0, description="Maximum delay between retries in seconds")
    backoff_factor: float = Field(default=2.0, ge=1.0, description="Multiplier applied to delay after each attempt")


class PluginInstanceConfig(BaseModel):
    """Base configuration for every plugin instance.

    Plugin authors subclass this to add their own config fields.
    The Pydantic JSON Schema (``model_json_schema()``) is used by the
    frontend to render dynamic configuration forms.
    """

    instance_name: str = Field(
        default="",
        min_length=1,
        max_length=100,
        description="Human-readable name for this plugin instance",
        json_schema_extra={"ui_order": 0},
    )
    demo_mode: bool = Field(
        default=True,
        description="When enabled, generate simulated data instead of reading real hardware",
        json_schema_extra={"ui_order": 1},
    )
    poll_interval_ms: int = Field(
        default=1000,
        ge=50,
        le=60000,
        description="Polling interval in milliseconds",
        json_schema_extra={"ui_order": 2},
    )
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)


@dataclass(frozen=True)
class PluginMeta:
    """Immutable metadata describing a plugin class (not an instance).

    This is set as a ``ClassVar`` on every plugin implementation.
    """

    id: str
    name: str
    version: str
    vendor: str = ""
    description: str = ""
    protocol: str = ""
    url: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "vendor": self.vendor,
            "description": self.description,
            "protocol": self.protocol,
            "url": self.url,
            "tags": list(self.tags),
        }
