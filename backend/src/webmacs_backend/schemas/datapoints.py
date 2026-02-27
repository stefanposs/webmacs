"""Datapoint schemas."""

from __future__ import annotations

import datetime  # noqa: TC003

from pydantic import BaseModel, Field


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


class DatapointSeriesRequest(BaseModel):
    event_public_ids: list[str] = Field(min_length=1, max_length=20)
    minutes: int = Field(default=60, ge=1, le=14400)
    max_points: int = Field(default=500, ge=10, le=2000)
