from __future__ import annotations

from pydantic import BaseModel, Field


class ServiceVersion(BaseModel):
    name: str
    installed: str | None = None
    available: str | None = None
    image: str | None = None


class VersionsResponse(BaseModel):
    services: list[ServiceVersion]


class UpdateTriggerRequest(BaseModel):
    backend_image: str | None = Field(default=None, max_length=512)
    frontend_image: str | None = Field(default=None, max_length=512)
    controller_image: str | None = Field(default=None, max_length=512)
    version: str | None = Field(default=None, max_length=64)
