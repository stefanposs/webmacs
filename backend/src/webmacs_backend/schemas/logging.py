"""Log entry schemas."""

from __future__ import annotations

import datetime  # noqa: TC003

from pydantic import BaseModel, Field

from webmacs_backend.enums import LoggingType, StatusType


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
    username: str | None = None

    model_config = {"from_attributes": True}
