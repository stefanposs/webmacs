"""OTA firmware update schemas."""

from __future__ import annotations

import datetime

from pydantic import BaseModel, Field, computed_field

from webmacs_backend.enums import UpdateStatus


class FirmwareUpdateCreate(BaseModel):
    version: str = Field(min_length=1, max_length=50, pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
    changelog: str | None = None


class FirmwareApplyRequest(BaseModel):
    download_url: str | None = Field(default=None, max_length=2048)
    file_hash_sha256: str | None = Field(default=None, min_length=64, max_length=64)


class FirmwareUpdateResponse(BaseModel):
    public_id: str
    version: str
    changelog: str | None = None
    file_path: str | None = Field(None, exclude=True)
    file_hash_sha256: str | None = None
    file_size_bytes: int | None = None
    status: UpdateStatus
    error_message: str | None = None
    created_on: datetime.datetime | None = None
    started_on: datetime.datetime | None = None
    completed_on: datetime.datetime | None = None
    user_public_id: str

    model_config = {"from_attributes": True}

    @computed_field  # type: ignore[misc]
    @property
    def has_firmware_file(self) -> bool:
        """True when a firmware binary has been uploaded."""
        return bool(self.file_path)


class UpdateCheckResponse(BaseModel):
    current_version: str
    latest_version: str | None = None
    update_available: bool
    # GitHub release info
    github_latest_version: str | None = None
    github_download_url: str | None = None
    github_release_url: str | None = None
    github_error: str | None = None
