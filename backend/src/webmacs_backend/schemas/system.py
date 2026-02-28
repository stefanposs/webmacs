"""Schemas for system-level endpoints (versions, update triggers)."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

# Only allow safe Docker image references: alphanumeric, slashes, dots, colons, dashes, underscores
_IMAGE_RE = re.compile(r"^[a-zA-Z0-9._/:@-]+$")


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

    @field_validator("backend_image", "frontend_image", "controller_image")
    @classmethod
    def validate_image_ref(cls, v: str | None) -> str | None:
        """Reject image references containing shell-unsafe characters."""
        if v is not None and not _IMAGE_RE.match(v):
            msg = f"Invalid Docker image reference: {v!r}"
            raise ValueError(msg)
        return v
