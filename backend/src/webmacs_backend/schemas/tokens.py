"""API token schemas."""

from __future__ import annotations

import datetime  # noqa: TC003

from pydantic import BaseModel, Field


class ApiTokenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    expires_at: datetime.datetime | None = None


class ApiTokenResponse(BaseModel):
    public_id: str
    name: str
    last_used_at: datetime.datetime | None = None
    expires_at: datetime.datetime | None = None
    created_at: datetime.datetime | None = None
    user_public_id: str = ""

    model_config = {"from_attributes": True}


class ApiTokenCreatedResponse(BaseModel):
    """Returned once when a token is created — includes the plaintext token."""

    public_id: str
    name: str
    token: str  # plaintext — shown only once
    expires_at: datetime.datetime | None = None
    created_at: datetime.datetime | None = None
