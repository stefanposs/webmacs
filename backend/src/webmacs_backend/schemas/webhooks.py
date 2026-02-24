"""Webhook and webhook delivery schemas."""

from __future__ import annotations

import datetime
import json
from typing import Any

from pydantic import BaseModel, Field, field_validator

from webmacs_backend.enums import WebhookDeliveryStatus, WebhookEventType


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
