"""Pydantic v2 schemas for request/response validation."""

import datetime

from pydantic import BaseModel, EmailStr, Field

from webmacs_backend.enums import EventType, LoggingType, StatusType


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
    datapoints: list[DatapointCreate]


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
