"""Expose installed and available versions and a trigger endpoint for direct Docker pulls.

This is a minimal implementation used by the frontend one-click update button.
The trigger endpoint runs pulls in the background and then attempts to restart the
compose stack using the `restart_services` helper from the updater service.
"""

from __future__ import annotations

import asyncio
import re
import subprocess
from typing import Iterable

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from webmacs_backend import __version__
from webmacs_backend.dependencies import AdminUser
from webmacs_backend.schemas.system import UpdateTriggerRequest, VersionsResponse, ServiceVersion
from webmacs_backend.schemas import StatusResponse
from webmacs_backend.services.updater import restart_services

logger = structlog.get_logger()

router = APIRouter()


def _extract_tag_from_image(image: str | None) -> str | None:
    if not image:
        return None
    # image may be 'repo/name:tag' or 'repo/name@sha256:...'
    if ":" in image and "@" not in image:
        return image.split(":", 1)[1]
    return None


def _pull_images(images: Iterable[str]) -> None:
    for img in images:
        if not img:
            continue
        try:
            logger.info("docker_pull_start", image=img)
            subprocess.run(["docker", "pull", img], check=True, capture_output=True, text=True)  # noqa: S603
            logger.info("docker_pull_success", image=img)
        except subprocess.CalledProcessError as exc:
            logger.error("docker_pull_failed", image=img, stderr=(exc.stderr or "").strip())


async def _perform_pull_and_restart(request: UpdateTriggerRequest) -> None:
    loop = asyncio.get_running_loop()
    images = [x for x in (request.backend_image, request.frontend_image, request.controller_image) if x]
    if images:
        await loop.run_in_executor(None, _pull_images, images)

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
async def trigger_update(request: UpdateTriggerRequest, background_tasks: BackgroundTasks, admin_user: AdminUser) -> StatusResponse:
    """Trigger a direct Docker pull + restart in background (admin only).

    The request accepts image references for the three services and/or a `version`.
    Returns immediately while the actual pull+restart runs asynchronously.
    """
    if not (request.backend_image or request.frontend_image or request.controller_image or request.version):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No images or version specified")

    background_tasks.add_task(_perform_pull_and_restart, request)
    return StatusResponse(status="accepted", message="Update trigger accepted and running in background.")
