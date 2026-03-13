"""Expose installed and available versions per service, with per-service status tracking.

Endpoints:
    GET  /versions         — installed + available version per service (Docker-detected)
    POST /trigger          — write a trigger file so the updater container performs pull+restart
    GET  /update-progress  — poll the current update status from the shared status file

Update IPC:
    The backend container has the Docker socket mounted read-only (sufficient for version
    detection but NOT for pull/restart). The ``updater`` container has read-write socket
    access. To trigger an update the backend writes a JSON trigger file to the shared
    ``updates`` Docker volume. The updater's polling loop detects it, performs
    ``docker pull + docker compose up``, and writes progress to a sibling status file.
    The backend's ``GET /update-progress`` endpoint reads that status file.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException, status

from webmacs_backend.dependencies import AdminUser, CurrentUser
from webmacs_backend.schemas import StatusResponse
from webmacs_backend.schemas.system import (
    ServiceStatus,
    ServiceVersion,
    UpdateProgressResponse,
    UpdateTriggerRequest,
    VersionsResponse,
)
from webmacs_backend.services.version_detector import get_all_service_versions

logger = structlog.get_logger()

router = APIRouter()

# Shared volume paths — must match WEBMACS_UPDATE_DIR env var in updater service
_UPDATE_DIR = Path(os.environ.get("WEBMACS_UPDATE_DIR", "/updates"))
_TRIGGER_FILE = _UPDATE_DIR / "trigger.json"
_STATUS_FILE = _UPDATE_DIR / "update-status.json"


def _extract_tag_from_image(image: str | None) -> str | None:
    """Extract the tag portion from a Docker image reference.

    Handles registry ports correctly, e.g. 'registry:5000/repo:v1' → 'v1'.
    """
    if not image:
        return None
    if "@" in image:
        return None
    last_slash = image.rfind("/")
    last_colon = image.rfind(":")
    if last_colon > last_slash:
        return image[last_colon + 1 :]
    return None


async def _get_github_latest() -> str | None:
    """Fetch the latest GitHub release version (non-blocking)."""
    try:
        from webmacs_backend.services.ota_service import check_github_releases

        result = await check_github_releases()
        return result.get("version")
    except Exception as exc:
        logger.debug("versions_github_fetch_failed", error=str(exc))
        return None


def _read_current_status() -> UpdateProgressResponse:
    """Read the current update status from the shared status file.

    Falls back to an idle response if the file does not exist or cannot be parsed.
    """
    try:
        if _STATUS_FILE.exists():
            data = json.loads(_STATUS_FILE.read_text())
            return UpdateProgressResponse(**data)
    except Exception as exc:  # pragma: no cover — defensive fallback
        logger.debug("status_file_read_failed", error=str(exc))
    return UpdateProgressResponse(overall_status="idle", services={})


def _write_trigger(request: UpdateTriggerRequest) -> None:
    """Write a trigger file to the shared updates volume.

    The updater container detects the file and executes the pull+restart.
    Raises RuntimeError when a trigger is already pending.
    """
    if _TRIGGER_FILE.exists():
        raise RuntimeError("An update trigger is already pending")

    images = [x for x in (request.backend_image, request.frontend_image, request.controller_image) if x]
    version = request.version or _extract_tag_from_image(request.backend_image) or "latest"

    _UPDATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": version,
        "images": images,
        "requested_at": datetime.now(UTC).isoformat(),
    }
    # Atomic write: tmp file + rename prevents the updater from reading partial JSON
    tmp_path = None
    with tempfile.NamedTemporaryFile(dir=_UPDATE_DIR, suffix=".tmp", delete=False, mode="w") as fd:
        tmp_path = fd.name
        try:
            fd.write(json.dumps(payload))
            fd.flush()
            os.fsync(fd.fileno())
        except BaseException:
            Path(tmp_path).unlink(missing_ok=True)
            raise
    try:
        os.rename(tmp_path, str(_TRIGGER_FILE))
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise
    logger.info("trigger_file_written", version=version, images=images)


@router.get("/versions", response_model=VersionsResponse)
async def get_versions(current_user: CurrentUser) -> VersionsResponse:
    """Return installed and available version information for all three services.

    Installed versions are detected via the Docker API (image tags).
    Available version is fetched from the GitHub Releases API.
    """
    detected = get_all_service_versions()

    # Fetch GitHub latest version (best-effort, non-blocking)
    github_version = await _get_github_latest()

    current_status = _read_current_status()
    is_updating = current_status.overall_status in ("pulling", "restarting")

    services = []
    for name in ("backend", "frontend", "controller"):
        info = detected[name]
        svc_status: ServiceStatus = "updating" if is_updating else info.status

        services.append(
            ServiceVersion(
                name=name,
                installed=info.installed,
                available=github_version,
                image=info.image,
                status=svc_status,
            )
        )

    return VersionsResponse(services=services)


@router.get("/update-progress", response_model=UpdateProgressResponse)
async def get_update_progress(current_user: CurrentUser) -> UpdateProgressResponse:
    """Poll the current update status from the shared status file (any authenticated user)."""
    return _read_current_status()


@router.post("/trigger", response_model=StatusResponse)
async def trigger_update(
    request: UpdateTriggerRequest,
    admin_user: AdminUser,
) -> StatusResponse:
    """Delegate a Docker pull + restart to the updater container (admin only).

    Writes a JSON trigger file to the shared ``updates`` volume. The updater container
    detects it within its next poll cycle (≤30 s) and performs the actual work,
    writing live progress to a sibling status file. Returns immediately.
    """
    if not (request.backend_image or request.frontend_image or request.controller_image or request.version):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No images or version specified")

    try:
        _write_trigger(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return StatusResponse(
        status="accepted",
        message="Update trigger written; updater will process within the next poll cycle.",
    )
