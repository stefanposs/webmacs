"""Authentication and SSO schemas."""

from __future__ import annotations

import datetime  # noqa: TC003

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, pattern=r"^[^@\s]+@[^@\s]+$")
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


class SsoConfigResponse(BaseModel):
    """Public SSO configuration (no secrets)."""

    enabled: bool
    provider_name: str
    authorize_url: str  # frontend navigates here to start SSO


class SsoAuthorizeResponse(BaseModel):
    """URL the frontend should redirect to."""

    redirect_url: str


class UserMeResponse(BaseModel):
    """Response for ``GET /auth/me``."""

    public_id: str
    email: str
    username: str
    admin: bool = False
    role: str = "viewer"
    registered_on: datetime.datetime
    sso_provider: str | None = None
    created_on: datetime.datetime | None = None

    model_config = {"from_attributes": True}
