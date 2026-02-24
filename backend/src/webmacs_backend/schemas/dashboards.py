"""Dashboard and widget schemas."""

from __future__ import annotations

import datetime

from pydantic import BaseModel, Field

from webmacs_backend.enums import WidgetType


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
