"""Pydantic v2 schemas for request/response validation.

This package exposes the same public symbols as the former ``schemas.py``
monolith so that all existing ``from webmacs_backend.schemas import ...``
imports continue to work without modification.

Add new schemas to the appropriate domain module and re-export them here.
"""

from __future__ import annotations

from webmacs_backend.schemas.auth import (
    LoginRequest,
    LoginResponse,
    SsoAuthorizeResponse,
    SsoConfigResponse,
    TokenData,
)
from webmacs_backend.schemas.common import (
    HealthResponse,
    PaginatedResponse,
    StatusResponse,
)
from webmacs_backend.schemas.dashboards import (
    DashboardCreate,
    DashboardResponse,
    DashboardUpdate,
    DashboardWidgetCreate,
    DashboardWidgetResponse,
    DashboardWidgetUpdate,
)
from webmacs_backend.schemas.datapoints import (
    DatapointBatchCreate,
    DatapointCreate,
    DatapointResponse,
    DatapointSeriesRequest,
)
from webmacs_backend.schemas.events import (
    EventCreate,
    EventResponse,
    EventUpdate,
    ExperimentCreate,
    ExperimentResponse,
    ExperimentUpdate,
)
from webmacs_backend.schemas.logging import (
    LogEntryCreate,
    LogEntryResponse,
    LogEntryUpdate,
)
from webmacs_backend.schemas.ota import (
    FirmwareApplyRequest,
    FirmwareUpdateCreate,
    FirmwareUpdateResponse,
    UpdateCheckResponse,
)
from webmacs_backend.schemas.plugins import (
    ChannelMappingCreate,
    ChannelMappingResponse,
    ChannelMappingUpdate,
    PluginInstanceCreate,
    PluginInstanceResponse,
    PluginInstanceUpdate,
    PluginMetaResponse,
    PluginPackageResponse,
)
from webmacs_backend.schemas.rules import (
    RuleCreate,
    RuleResponse,
    RuleUpdate,
)
from webmacs_backend.schemas.system import (
    ServiceVersion,
    UpdateTriggerRequest,
    VersionsResponse,
)
from webmacs_backend.schemas.tokens import (
    ApiTokenCreate,
    ApiTokenCreatedResponse,
    ApiTokenResponse,
)
from webmacs_backend.schemas.users import (
    UserCreate,
    UserResponse,
    UserUpdate,
)
from webmacs_backend.schemas.webhooks import (
    WebhookCreate,
    WebhookDeliveryResponse,
    WebhookResponse,
    WebhookUpdate,
)

__all__ = [
    # tokens
    "ApiTokenCreate",
    "ApiTokenCreatedResponse",
    "ApiTokenResponse",
    "ChannelMappingCreate",
    "ChannelMappingResponse",
    "ChannelMappingUpdate",
    "DashboardCreate",
    "DashboardResponse",
    "DashboardUpdate",
    # dashboards
    "DashboardWidgetCreate",
    "DashboardWidgetResponse",
    "DashboardWidgetUpdate",
    "DatapointBatchCreate",
    # datapoints
    "DatapointCreate",
    "DatapointResponse",
    "DatapointSeriesRequest",
    # events & experiments
    "EventCreate",
    "EventResponse",
    "EventUpdate",
    "ExperimentCreate",
    "ExperimentResponse",
    "ExperimentUpdate",
    "FirmwareApplyRequest",
    # ota
    "FirmwareUpdateCreate",
    "FirmwareUpdateResponse",
    "HealthResponse",
    # logging
    "LogEntryCreate",
    "LogEntryResponse",
    "LogEntryUpdate",
    # auth
    "LoginRequest",
    "LoginResponse",
    # common
    "PaginatedResponse",
    "PluginInstanceCreate",
    "PluginInstanceResponse",
    "PluginInstanceUpdate",
    # plugins
    "PluginMetaResponse",
    "PluginPackageResponse",
    # rules
    "RuleCreate",
    "RuleResponse",
    "RuleUpdate",
    # system
    "ServiceVersion",
    "SsoAuthorizeResponse",
    "SsoConfigResponse",
    "StatusResponse",
    "TokenData",
    "UpdateCheckResponse",
    "UpdateTriggerRequest",
    # users
    "UserCreate",
    "UserResponse",
    "UserUpdate",
    "VersionsResponse",
    # webhooks
    "WebhookCreate",
    "WebhookDeliveryResponse",
    "WebhookResponse",
    "WebhookUpdate",
]
