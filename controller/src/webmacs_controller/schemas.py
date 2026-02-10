"""Pydantic v2 schemas for controller data models."""

from enum import Enum

from pydantic import BaseModel


class EventType(str, Enum):
    sensor = "sensor"
    actuator = "actuator"
    range = "range"
    cmd_button = "cmd_button"
    cmd_opened = "cmd_opened"
    cmd_closed = "cmd_closed"


class EventSchema(BaseModel):
    """Schema for event data from the backend API."""

    public_id: str
    name: str
    min_value: float
    max_value: float
    unit: str
    type: EventType
    user_public_id: str | None = None


class EventListResponse(BaseModel):
    """Paginated event list response."""

    page: int
    page_size: int
    total: int
    data: list[EventSchema]


class DatapointSchema(BaseModel):
    """Schema for datapoint data."""

    public_id: str | None = None
    value: float
    timestamp: str | None = None
    event_public_id: str
    experiment_public_id: str | None = None


class DatapointBatchRequest(BaseModel):
    """Batch datapoint creation request."""

    datapoints: list[DatapointSchema]


class LoginRequest(BaseModel):
    """Authentication request."""

    email: str
    password: str


class LoginResponse(BaseModel):
    """Authentication response."""

    status: str
    access_token: str
    public_id: str
    username: str
