"""Expose installed and available versions and a trigger endpoint for direct Docker pulls.

This is a minimal implementation used by the frontend one-click update button.
The trigger endpoint runs pulls in the background and then attempts to restart the
compose stack using the `restart_services` helper from the updater service.
"""

from __future__ import annotations

import asyncio

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from webmacs_backend import __version__
from webmacs_backend.dependencies import AdminUser
from webmacs_backend.schemas import StatusResponse
from webmacs_backend.schemas.system import ServiceVersion, UpdateTriggerRequest, VersionsResponse
from webmacs_backend.services.updater import pull_images, restart_services

logger = structlog.get_logger()

router = APIRouter()

# Prevent concurrent trigger calls from racing
_update_lock = asyncio.Lock()


def _extract_tag_from_image(image: str | None) -> str | None:
    """Extract the tag portion from a Docker image reference.

    Handles registry ports correctly, e.g. 'registry:5000/repo:v1' → 'v1'.
    """
    if not image:
        return None
    # Ignore digest-pinned refs
    if "@" in image:
        return None
    # Split off the last ':' only if it appears after the last '/'
    last_slash = image.rfind("/")
    last_colon = image.rfind(":")
    if last_colon > last_slash:
        return image[last_colon + 1 :]
    return None


async def _perform_pull_and_restart(request: UpdateTriggerRequest) -> None:
    loop = asyncio.get_running_loop()
    images = [x for x in (request.backend_image, request.frontend_image, request.controller_image) if x]
    if images:
        ok = await loop.run_in_executor(None, pull_images, images)
        if not ok:
            logger.error("trigger_pull_failed", images=images)
            return  # abort — don't restart with broken images

    # Determine version to persist/restart with
    version = request.version
    if not version:
        version = _extract_tag_from_image(request.backend_image) or __version__

    # Attempt restart; restart_services will persist version when applicable
    try:
        ok = await loop.run_in_executor(None, restart_services, version)
        if not ok:
            logger.error("trigger_restart_failed", version=version)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("trigger_restart_exception", error=str(exc))


@router.get("/versions", response_model=VersionsResponse)
async def get_versions() -> VersionsResponse:
    """Return installed (server-side) version information for services.

    This endpoint intentionally returns minimal data useful for the frontend view.
    More advanced available-version checks (GitHub Releases) are performed by the
    frontend or background jobs and are not required for the one-click trigger flow.
    """
    services = [
        ServiceVersion(name="backend", installed=__version__, available=None, image=None),
        ServiceVersion(name="frontend", installed=None, available=None, image=None),
        ServiceVersion(name="controller", installed=None, available=None, image=None),
    ]
    return VersionsResponse(services=services)


@router.post("/trigger", response_model=StatusResponse)
async def trigger_update(
    request: UpdateTriggerRequest,
    background_tasks: BackgroundTasks,
    admin_user: AdminUser,
) -> StatusResponse:
    """Trigger a direct Docker pull + restart in background (admin only).

    The request accepts image references for the three services and/or a `version`.
    Returns immediately while the actual pull+restart runs asynchronously.
    """
    if not (request.backend_image or request.frontend_image or request.controller_image or request.version):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No images or version specified")

    if _update_lock.locked():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An update is already in progress")

    async def _guarded_update() -> None:
        async with _update_lock:
            await _perform_pull_and_restart(request)

    background_tasks.add_task(_guarded_update)
    return StatusResponse(status="accepted", message="Update trigger accepted and running in background.")
