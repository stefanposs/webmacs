"""Expose installed and available versions per service, with per-service status tracking.

Endpoints:
    GET  /versions         — installed + available version per service (Docker-detected)
    POST /trigger          — pull latest images + restart (admin-only, background)
    GET  /update-progress  — poll the current background update status
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from webmacs_backend.dependencies import AdminUser, CurrentUser
from webmacs_backend.schemas import StatusResponse
from webmacs_backend.schemas.system import (
    ServiceStatus,
    ServiceVersion,
    UpdateProgressResponse,
    UpdateTriggerRequest,
    VersionsResponse,
)
from webmacs_backend.services.updater import pull_images, restart_services
from webmacs_backend.services.version_detector import get_all_service_versions

logger = structlog.get_logger()

router = APIRouter()

# Prevent concurrent trigger calls from racing
_update_lock = asyncio.Lock()

# Global in-process update progress (reset on each new trigger)
_update_progress: UpdateProgressResponse = UpdateProgressResponse(
    overall_status="idle",
    services={},
)


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


async def _perform_pull_and_restart(request: UpdateTriggerRequest) -> None:
    global _update_progress  # noqa: PLW0603

    def _set(overall: str, step: str, svc_statuses: dict[str, str], err: str | None = None) -> None:
        global _update_progress  # noqa: PLW0603
        _update_progress = UpdateProgressResponse(
            overall_status=overall,  # type: ignore[arg-type]
            services=svc_statuses,  # type: ignore[arg-type]
            current_step=step,
            started_at=_update_progress.started_at,
            error=err,
        )

    started_at = datetime.now(UTC).isoformat()
    _update_progress = UpdateProgressResponse(
        overall_status="pulling",
        services={
            "backend": "updating",
            "frontend": "updating",
            "controller": "updating",
        },
        current_step="Pulling images…",
        started_at=started_at,
    )

    loop = asyncio.get_running_loop()
    images = [x for x in (request.backend_image, request.frontend_image, request.controller_image) if x]
    if images:
        ok = await loop.run_in_executor(None, pull_images, images)
        if not ok:
            logger.error("trigger_pull_failed", images=images)
            svc_err = dict.fromkeys(("backend", "frontend", "controller"), "error")
            _set("failed", "Image pull failed", svc_err, "Image pull failed")  # type: ignore[arg-type]
            return

    _set("restarting", "Restarting services…", dict.fromkeys(("backend", "frontend", "controller"), "updating"))  # type: ignore[arg-type]

    version = request.version
    if not version:
        version = _extract_tag_from_image(request.backend_image) or "latest"

    try:
        ok = await loop.run_in_executor(None, restart_services, version)
        if ok:
            logger.info("trigger_restart_success", version=version)
            svc_ok = dict.fromkeys(("backend", "frontend", "controller"), "running")
            _set("completed", "Update completed", svc_ok)  # type: ignore[arg-type]
        else:
            logger.error("trigger_restart_failed", version=version)
            svc_err = dict.fromkeys(("backend", "frontend", "controller"), "error")
            _set("failed", "Restart failed", svc_err, "Service restart failed")  # type: ignore[arg-type]
    except Exception as exc:  # pragma: no cover
        logger.error("trigger_restart_exception", error=str(exc))
        svc_err = dict.fromkeys(("backend", "frontend", "controller"), "error")
        _set("failed", str(exc), svc_err, str(exc))  # type: ignore[arg-type]


@router.get("/versions", response_model=VersionsResponse)
async def get_versions(current_user: CurrentUser) -> VersionsResponse:
    """Return installed and available version information for all three services.

    Installed versions are detected via the Docker API (image tags).
    Available version is fetched from the GitHub Releases API.
    """
    detected = get_all_service_versions()

    # Fetch GitHub latest version (best-effort, non-blocking)
    github_version = await _get_github_latest()

    services = []
    for name in ("backend", "frontend", "controller"):
        info = detected[name]
        # While an update is running, mark each service as "updating"
        updating = _update_progress.overall_status in ("pulling", "restarting")
        svc_status: ServiceStatus = "updating" if updating else info.status

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
    """Poll the current background update status (any authenticated user)."""
    return _update_progress


@router.post("/trigger", response_model=StatusResponse)
async def trigger_update(
    request: UpdateTriggerRequest,
    background_tasks: BackgroundTasks,
    admin_user: AdminUser,
) -> StatusResponse:
    """Trigger a direct Docker pull + restart in background (admin only).

    The request accepts image references for the three services and/or a ``version``.
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
