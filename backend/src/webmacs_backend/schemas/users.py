"""User schemas."""

from __future__ import annotations

import datetime  # noqa: TC003

from pydantic import BaseModel, EmailStr, Field

from webmacs_backend.enums import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=8)
    role: UserRole = UserRole.viewer


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = Field(default=None, min_length=2, max_length=50)
    password: str | None = Field(default=None, min_length=8)
    role: UserRole | None = None


class UserResponse(BaseModel):
    public_id: str
    email: str
    username: str
    role: UserRole
    admin: bool = False
    registered_on: datetime.datetime
    sso_provider: str | None = None

    model_config = {"from_attributes": True}
