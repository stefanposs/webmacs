"""Plugin instance, channel mapping, and package schemas."""

from __future__ import annotations

import datetime
import json

from pydantic import BaseModel, Field, field_validator

from webmacs_backend.enums import ChannelDirection, PluginSource, PluginStatus


class PluginMetaResponse(BaseModel):
    """Metadata about an available (installed) plugin class."""

    id: str
    name: str
    version: str
    vendor: str
    description: str
    url: str | None = None


class PluginInstanceCreate(BaseModel):
    plugin_id: str = Field(min_length=1, max_length=100)
    instance_name: str = Field(min_length=1, max_length=255)
    demo_mode: bool = False
    enabled: bool = True
    auto_create_events: bool = True
    config_json: str | None = None


class PluginInstanceUpdate(BaseModel):
    instance_name: str | None = Field(default=None, min_length=1, max_length=255)
    demo_mode: bool | None = None
    enabled: bool | None = None
    config_json: str | None = None


class ChannelMappingCreate(BaseModel):
    channel_id: str = Field(min_length=1, max_length=100)
    channel_name: str = Field(min_length=1, max_length=255)
    direction: ChannelDirection
    unit: str = Field(min_length=1, max_length=50)
    event_public_id: str | None = None


class ChannelMappingUpdate(BaseModel):
    event_public_id: str | None = None


class ChannelMappingResponse(BaseModel):
    public_id: str
    channel_id: str
    channel_name: str
    direction: ChannelDirection
    unit: str
    event_public_id: str | None = None
    created_on: datetime.datetime | None = None

    model_config = {"from_attributes": True}


class PluginInstanceResponse(BaseModel):
    public_id: str
    plugin_id: str
    instance_name: str
    demo_mode: bool
    enabled: bool
    status: PluginStatus
    config_json: str | None = None
    error_message: str | None = None
    created_on: datetime.datetime | None = None
    updated_on: datetime.datetime | None = None
    user_public_id: str
    channel_mappings: list[ChannelMappingResponse] = []

    model_config = {"from_attributes": True}


class PluginPackageResponse(BaseModel):
    """Info about an installed plugin package."""

    public_id: str
    package_name: str
    version: str
    source: PluginSource
    plugin_ids: list[str] = []
    file_size_bytes: int | None = None
    installed_on: datetime.datetime | None = None
    removable: bool = False

    @field_validator("plugin_ids", mode="before")
    @classmethod
    def _parse_plugin_ids(cls, v: object) -> list[str]:
        """Accept JSON string or list from ORM."""
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
            except json.JSONDecodeError:
                return []
            return parsed if isinstance(parsed, list) else []
        return v if isinstance(v, list) else []

    model_config = {"from_attributes": True}
