"""Event and Experiment schemas."""

from __future__ import annotations

import datetime

from pydantic import BaseModel, Field

from webmacs_backend.enums import EventType


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
