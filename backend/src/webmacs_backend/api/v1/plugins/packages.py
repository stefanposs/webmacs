"""Plugin package management — upload, list, and uninstall ``.whl`` packages."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import subprocess
import uuid
from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException, UploadFile, status
from sqlalchemy import select

from webmacs_backend.dependencies import AdminUser, DbSession, ViewerUser
from webmacs_backend.enums import PluginSource
from webmacs_backend.models import PluginPackage
from webmacs_backend.repository import get_or_404
from webmacs_backend.schemas import PluginPackageResponse, StatusResponse
from webmacs_backend.services.wheel_validator import InvalidWheelError, validate_wheel

router = APIRouter(prefix="/packages")
logger = structlog.get_logger()

PLUGIN_DIR = Path(os.environ.get("WEBMACS_PLUGIN_DIR", "/plugins"))
MAX_WHEEL_SIZE = 50 * 1024 * 1024  # 50 MB


@router.get("", response_model=list[PluginPackageResponse])
async def list_plugin_packages(
    db: DbSession,
    current_user: ViewerUser,
) -> list[PluginPackageResponse]:
    """List all installed plugin packages (bundled + uploaded)."""
    result = await db.execute(
        select(PluginPackage).order_by(PluginPackage.installed_on),
    )
    packages = []
    for pkg in result.scalars().all():
        resp = PluginPackageResponse.model_validate(pkg)
        resp.removable = pkg.source == PluginSource.uploaded
        packages.append(resp)
    return packages


@router.post(
    "/upload",
    response_model=StatusResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_plugin_package(
    file: UploadFile,
    db: DbSession,
    admin_user: AdminUser,
) -> StatusResponse:
    """Upload a ``.whl`` plugin package (admin only).

    The wheel is validated for correct structure, saved to disk, then
    installed via ``pip install --no-deps``.  After install, the new
    plugin(s) are discovered and recorded in the database.
    """
    if not file.filename or not file.filename.endswith(".whl"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a .whl (Python wheel) package.",
        )

    # Stream to temp location
    PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
    dest = PLUGIN_DIR / file.filename

    if dest.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Package '{file.filename}' already exists.",
        )

    sha256 = hashlib.sha256()
    total = 0
    with dest.open("wb") as f:
        while chunk := await file.read(64 * 1024):
            total += len(chunk)
            if total > MAX_WHEEL_SIZE:
                f.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Wheel exceeds maximum size (50 MB).",
                )
            sha256.update(chunk)
            f.write(chunk)

    # Validate wheel structure
    try:
        info = validate_wheel(dest)
    except InvalidWheelError as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    # Check for duplicate package name in DB
    existing = await db.execute(
        select(PluginPackage).where(
            PluginPackage.package_name == info.name,
        ),
    )
    if existing.scalar_one_or_none():
        dest.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Plugin package '{info.name}' is already installed. "
                "Remove it first to upload a new version."
            ),
        )

    # Install the wheel (run in thread to avoid blocking the async event loop)
    result = await asyncio.to_thread(
        subprocess.run,
        [
            "uv",
            "pip",
            "install",
            "--system",
            "--no-deps",
            "--reinstall",
            str(dest),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        dest.unlink(missing_ok=True)
        logger.error(
            "plugin_pip_install_failed",
            stderr=result.stderr[:500],
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Plugin install failed: {result.stderr[:300]}",
        )

    # Discover which plugin IDs the new package provides
    plugin_ids: list[str] = []
    try:
        from webmacs_plugins_core.discovery import discover_plugins

        found = discover_plugins()
        # Match by package name convention
        for pid, cls in found.items():
            pkg_candidate = f"webmacs-plugin-{pid}"
            if pkg_candidate == info.name or info.name in str(
                type(cls).__module__,
            ):
                plugin_ids.append(pid)
        # Fallback: if no match, store all newly discovered
        if not plugin_ids:
            plugin_ids = list(found.keys())
    except Exception:
        logger.warning("plugin_discovery_after_install_failed", package=info.name)

    # Record in DB
    pkg = PluginPackage(
        public_id=str(uuid.uuid4()),
        package_name=info.name,
        version=info.version,
        source=PluginSource.uploaded,
        file_path=str(dest),
        file_hash_sha256=sha256.hexdigest(),
        file_size_bytes=total,
        plugin_ids=json.dumps(plugin_ids),
        user_public_id=admin_user.public_id,
    )
    db.add(pkg)

    logger.info(
        "plugin_package_uploaded",
        package=info.name,
        version=info.version,
        plugins=plugin_ids,
        size=total,
    )
    return StatusResponse(
        status="success",
        message=(
            f"Plugin package '{info.name}' v{info.version} "
            f"installed ({total:,} bytes). "
            f"Restart the controller to activate."
        ),
    )


@router.delete(
    "/{public_id}",
    response_model=StatusResponse,
)
async def uninstall_plugin_package(
    public_id: str,
    db: DbSession,
    admin_user: AdminUser,
) -> StatusResponse:
    """Uninstall an uploaded plugin package (admin only).

    Bundled packages cannot be removed.
    """
    pkg = await get_or_404(
        db,
        PluginPackage,
        public_id,
        entity_name="Plugin package",
    )
    if pkg.source == PluginSource.bundled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bundled plugins cannot be removed.",
        )

    # Validate package name before passing to subprocess
    if not re.match(r"^[a-zA-Z0-9._-]+$", pkg.package_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid package name.",
        )

    # uv pip uninstall (run in thread to avoid blocking the async event loop)
    result = await asyncio.to_thread(
        subprocess.run,
        ["uv", "pip", "uninstall", "--system", pkg.package_name],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        logger.warning(
            "plugin_pip_uninstall_failed",
            stderr=result.stderr[:500],
        )

    # Remove wheel file
    if pkg.file_path:
        Path(pkg.file_path).unlink(missing_ok=True)

    # Remove DB record
    await db.delete(pkg)

    logger.info("plugin_package_uninstalled", package=pkg.package_name)
    return StatusResponse(
        status="success",
        message=(
            f"Plugin package '{pkg.package_name}' uninstalled. "
            "Restart the controller to apply."
        ),
    )
