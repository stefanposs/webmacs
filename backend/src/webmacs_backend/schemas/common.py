"""Shared / common schemas used across multiple domains."""

from __future__ import annotations

import datetime

from pydantic import BaseModel


class PaginatedResponse[T](BaseModel):
    page: int
    page_size: int
    total: int
    data: list[T]


class StatusResponse(BaseModel):
    status: str
    message: str


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    last_datapoint: datetime.datetime | None = None
    uptime_seconds: float | None = None
