"""Pydantic v2 schemas for request/response validation."""

from __future__ import annotations

import datetime
import json
from typing import Any

from pydantic import BaseModel, EmailStr, Field, computed_field, field_validator, model_validator

from webmacs_backend.enums import (
    ChannelDirection,
    EventType,
    LoggingType,
    PluginSource,
    PluginStatus,
    RuleActionType,
    RuleOperator,
    StatusType,
    UpdateStatus,
    WebhookDeliveryStatus,
    WebhookEventType,
    WidgetType,
)

# ─── Auth ────────────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    status: str = "success"
    message: str = "Successfully logged in."
    access_token: str
    public_id: str
    username: str


class TokenData(BaseModel):
    user_id: int
    exp: datetime.datetime


# ─── User ────────────────────────────────────────────────────────────────────


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=8)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = Field(default=None, min_length=2, max_length=50)
    password: str | None = Field(default=None, min_length=8)


class UserResponse(BaseModel):
    public_id: str
    email: str
    username: str
    admin: bool
    registered_on: datetime.datetime

    model_config = {"from_attributes": True}


# ─── Event ───────────────────────────────────────────────────────────────────


class EventCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    min_value: float
    max_value: float
    unit: str = Field(min_length=1, max_length=255)
    type: EventType


class EventUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    min_value: float | None = None
    max_value: float | None = None
    unit: str | None = None
    type: EventType | None = None


class EventResponse(BaseModel):
    public_id: str
    name: str
    min_value: float
    max_value: float
    unit: str
    type: EventType
    user_public_id: str | None = None

    model_config = {"from_attributes": True}


# ─── Experiment ──────────────────────────────────────────────────────────────


class ExperimentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ExperimentUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)


class ExperimentResponse(BaseModel):
    public_id: str
    name: str
    started_on: datetime.datetime | None = None
    stopped_on: datetime.datetime | None = None
    user_public_id: str | None = None

    model_config = {"from_attributes": True}


# ─── Datapoint ───────────────────────────────────────────────────────────────


class DatapointCreate(BaseModel):
    value: float
    event_public_id: str


class DatapointBatchCreate(BaseModel):
    datapoints: list[DatapointCreate] = Field(max_length=500)


class DatapointResponse(BaseModel):
    public_id: str
    value: float
    timestamp: datetime.datetime | None = None
    event_public_id: str
    experiment_public_id: str | None = None

    model_config = {"from_attributes": True}


# ─── Logging ─────────────────────────────────────────────────────────────────


class LogEntryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    logging_type: LoggingType = LoggingType.info


class LogEntryUpdate(BaseModel):
    status_type: StatusType | None = None
    content: str | None = None


class LogEntryResponse(BaseModel):
    public_id: str
    content: str
    logging_type: LoggingType | None = None
    status_type: StatusType | None = None
    created_on: datetime.datetime | None = None
    user_public_id: str

    model_config = {"from_attributes": True}


# ─── Pagination ──────────────────────────────────────────────────────────────


class PaginatedResponse[T](BaseModel):
    page: int
    page_size: int
    total: int
    data: list[T]


# ─── Generic ─────────────────────────────────────────────────────────────────


class StatusResponse(BaseModel):
    status: str
    message: str


# ─── Webhook ─────────────────────────────────────────────────────────────────


class WebhookCreate(BaseModel):
    url: str = Field(min_length=1, max_length=2048, pattern=r"^https?://")
    secret: str | None = Field(default=None, max_length=255)
    events: list[WebhookEventType] = Field(min_length=1)
    enabled: bool = True


class WebhookUpdate(BaseModel):
    url: str | None = Field(default=None, max_length=2048, pattern=r"^https?://")
    secret: str | None = None
    events: list[WebhookEventType] | None = None
    enabled: bool | None = None


class WebhookResponse(BaseModel):
    public_id: str
    url: str
    events: list[str]
    enabled: bool
    created_on: datetime.datetime | None = None
    user_public_id: str
    model_config = {"from_attributes": True}

    @field_validator("events", mode="before")
    @classmethod
    def _parse_events_json(cls, v: Any) -> list[str]:
        """Deserialize JSON text from DB column to list."""
        if isinstance(v, str):
            import json

            try:
                parsed: list[str] = json.loads(v)
                return parsed
            except (json.JSONDecodeError, TypeError):
                return []
        return list(v)


class WebhookDeliveryResponse(BaseModel):
    public_id: str
    event_type: str
    status: WebhookDeliveryStatus
    attempts: int
    last_error: str | None = None
    response_code: int | None = None
    created_on: datetime.datetime | None = None
    delivered_on: datetime.datetime | None = None

    model_config = {"from_attributes": True}


# ─── Health ──────────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    last_datapoint: datetime.datetime | None = None
    uptime_seconds: float | None = None


# ─── Rule (Event Engine LITE) ───────────────────────────────────────────────


class RuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    event_public_id: str
    operator: RuleOperator
    threshold: float
    threshold_high: float | None = None
    action_type: RuleActionType
    webhook_event_type: WebhookEventType | None = None
    enabled: bool = True
    cooldown_seconds: int = Field(default=60, ge=0)

    @model_validator(mode="after")
    def validate_rule_consistency(self) -> RuleCreate:
        """Cross-field validation for rule configuration."""
        if self.operator in (RuleOperator.between, RuleOperator.not_between):
            if self.threshold_high is None:
                msg = "threshold_high is required for between/not_between operators"
                raise ValueError(msg)
            if self.threshold_high < self.threshold:
                msg = "threshold_high must be >= threshold"
                raise ValueError(msg)
        return self


class RuleUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    event_public_id: str | None = None
    operator: RuleOperator | None = None
    threshold: float | None = None
    threshold_high: float | None = None
    action_type: RuleActionType | None = None
    webhook_event_type: WebhookEventType | None = None
    enabled: bool | None = None
    cooldown_seconds: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_rule_consistency(self) -> RuleUpdate:
        """Cross-field validation for between/not_between operators."""
        if self.operator in (RuleOperator.between, RuleOperator.not_between):
            if self.threshold is not None and self.threshold_high is None:
                msg = "threshold_high is required for between/not_between operators"
                raise ValueError(msg)
            if self.threshold is not None and self.threshold_high is not None and self.threshold_high < self.threshold:
                msg = "threshold_high must be >= threshold"
                raise ValueError(msg)
        return self


class RuleResponse(BaseModel):
    public_id: str
    name: str
    event_public_id: str
    operator: RuleOperator
    threshold: float
    threshold_high: float | None = None
    action_type: RuleActionType
    webhook_event_type: str | None = None
    enabled: bool
    cooldown_seconds: int
    last_triggered_at: datetime.datetime | None = None
    created_on: datetime.datetime | None = None
    user_public_id: str

    model_config = {"from_attributes": True}


# ─── OTA Updates ─────────────────────────────────────────────────────────────


class FirmwareUpdateCreate(BaseModel):
    version: str = Field(min_length=1, max_length=50, pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
    changelog: str | None = None


class FirmwareApplyRequest(BaseModel):
    download_url: str | None = Field(default=None, max_length=2048)
    file_hash_sha256: str | None = Field(default=None, min_length=64, max_length=64)


class FirmwareUpdateResponse(BaseModel):
    public_id: str
    version: str
    changelog: str | None = None
    file_path: str | None = Field(None, exclude=True)
    file_hash_sha256: str | None = None
    file_size_bytes: int | None = None
    status: UpdateStatus
    error_message: str | None = None
    created_on: datetime.datetime | None = None
    started_on: datetime.datetime | None = None
    completed_on: datetime.datetime | None = None
    user_public_id: str

    model_config = {"from_attributes": True}

    @computed_field  # type: ignore[misc]
    @property
    def has_firmware_file(self) -> bool:
        """True when a firmware binary has been uploaded."""
        return bool(self.file_path)


class UpdateCheckResponse(BaseModel):
    current_version: str
    latest_version: str | None = None
    update_available: bool
    # GitHub release info
    github_latest_version: str | None = None
    github_download_url: str | None = None
    github_release_url: str | None = None
    github_error: str | None = None


# ─── Dashboard ───────────────────────────────────────────────────────────────


class DashboardWidgetCreate(BaseModel):
    widget_type: WidgetType
    title: str = Field(min_length=1, max_length=255)
    event_public_id: str | None = None
    x: int = 0
    y: int = 0
    w: int = Field(default=4, ge=1, le=12)
    h: int = Field(default=3, ge=1, le=12)
    config_json: str | None = None


class DashboardWidgetUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    event_public_id: str | None = None
    x: int | None = None
    y: int | None = None
    w: int | None = Field(default=None, ge=1, le=12)
    h: int | None = Field(default=None, ge=1, le=12)
    config_json: str | None = None


class DashboardWidgetResponse(BaseModel):
    public_id: str
    widget_type: WidgetType
    title: str
    event_public_id: str | None = None
    x: int
    y: int
    w: int
    h: int
    config_json: str | None = None

    model_config = {"from_attributes": True}


class DashboardCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    is_global: bool = False


class DashboardUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    is_global: bool | None = None


class DashboardResponse(BaseModel):
    public_id: str
    name: str
    is_global: bool
    created_on: datetime.datetime | None = None
    user_public_id: str
    widgets: list[DashboardWidgetResponse] = []

    model_config = {"from_attributes": True}


# ─── Datapoint Series ───────────────────────────────────────────────────────


class DatapointSeriesRequest(BaseModel):
    event_public_ids: list[str] = Field(min_length=1, max_length=20)
    minutes: int = Field(default=60, ge=1, le=14400)
    max_points: int = Field(default=500, ge=10, le=2000)


# ─── Plugin ──────────────────────────────────────────────────────────────────


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


# ─── Plugin Packages ────────────────────────────────────────────────────────────


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
