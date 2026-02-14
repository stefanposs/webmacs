"""Plugin management endpoints — install, configure, and map device plugins."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import uuid
from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from webmacs_backend.dependencies import AdminUser, CurrentUser, DbSession
from webmacs_backend.enums import PluginSource
from webmacs_backend.models import ChannelMapping, DashboardWidget, Event, PluginInstance, PluginPackage
from webmacs_backend.repository import ConflictError, delete_by_public_id, get_or_404, paginate, update_from_schema
from webmacs_backend.schemas import (
    ChannelMappingCreate,
    ChannelMappingResponse,
    ChannelMappingUpdate,
    PaginatedResponse,
    PluginInstanceCreate,
    PluginInstanceResponse,
    PluginInstanceUpdate,
    PluginMetaResponse,
    PluginPackageResponse,
    StatusResponse,
)
from webmacs_backend.services.wheel_validator import InvalidWheelError, validate_wheel

router = APIRouter()
logger = structlog.get_logger()

PLUGIN_DIR = Path(os.environ.get("WEBMACS_PLUGIN_DIR", "/plugins"))
MAX_WHEEL_SIZE = 50 * 1024 * 1024  # 50 MB


# ─── Available plugins (discovery) ──────────────────────────────────────────


@router.get("/available", response_model=list[PluginMetaResponse])
async def list_available_plugins(current_user: CurrentUser) -> list[PluginMetaResponse]:
    """List all installed plugin classes (discovered via entry_points)."""
    try:
        from webmacs_plugins_core.discovery import discover_plugins

        found = discover_plugins()
        return [
            PluginMetaResponse(
                id=cls.meta.id,
                name=cls.meta.name,
                version=cls.meta.version,
                vendor=cls.meta.vendor,
                description=cls.meta.description,
                url=cls.meta.url,
            )
            for cls in found.values()
        ]
    except Exception:
        logger.exception("plugin_discovery_failed")
        return []


# ─── Plugin packages (upload / manage) ──────────────────────────────────────
# NOTE: These routes MUST be registered before /{public_id} to avoid
# FastAPI matching "packages" as a path parameter.


@router.get("/packages", response_model=list[PluginPackageResponse])
async def list_plugin_packages(
    db: DbSession,
    current_user: CurrentUser,
) -> list[PluginPackageResponse]:
    """List all installed plugin packages (bundled + uploaded)."""
    result = await db.execute(
        select(PluginPackage).order_by(PluginPackage.installed_on),
    )
    packages = []
    for pkg in result.scalars().all():
        resp = PluginPackageResponse.model_validate(pkg)
        # Parse the JSON plugin_ids
        try:
            resp.plugin_ids = json.loads(pkg.plugin_ids)
        except (json.JSONDecodeError, TypeError):
            resp.plugin_ids = []
        resp.removable = pkg.source == PluginSource.uploaded
        packages.append(resp)
    return packages


@router.post(
    "/packages/upload",
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
            detail=(f"Plugin package '{info.name}' is already installed. Remove it first to upload a new version."),
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
    "/packages/{public_id}",
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

    # pip uninstall (run in thread to avoid blocking the async event loop)
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
        message=(f"Plugin package '{pkg.package_name}' uninstalled. Restart the controller to apply."),
    )


# ─── Plugin instances CRUD ───────────────────────────────────────────────────


@router.get("", response_model=PaginatedResponse[PluginInstanceResponse])
async def list_plugin_instances(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> PaginatedResponse[PluginInstanceResponse]:
    base_query = select(PluginInstance).options(selectinload(PluginInstance.channel_mappings))
    return await paginate(
        db,
        PluginInstance,
        PluginInstanceResponse,
        page=page,
        page_size=page_size,
        base_query=base_query,
    )


@router.post("", response_model=StatusResponse, status_code=status.HTTP_201_CREATED)
async def create_plugin_instance(
    data: PluginInstanceCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> StatusResponse:
    result = await db.execute(select(PluginInstance).where(PluginInstance.instance_name == data.instance_name))
    if result.scalar_one_or_none():
        raise ConflictError("Plugin instance")

    instance = PluginInstance(
        public_id=str(uuid.uuid4()),
        plugin_id=data.plugin_id,
        instance_name=data.instance_name,
        demo_mode=data.demo_mode,
        enabled=data.enabled,
        config_json=data.config_json,
        user_public_id=current_user.public_id,
    )
    db.add(instance)
    await db.flush()

    # Auto-discover channels from the plugin class and create mappings + events
    try:
        from webmacs_plugins_core.discovery import discover_plugins

        plugins = discover_plugins()
        plugin_cls = plugins.get(data.plugin_id)
        if plugin_cls:
            plugin = plugin_cls()
            config = json.loads(data.config_json) if data.config_json else {}
            config["demo_mode"] = data.demo_mode
            plugin.configure(config)
            for ch_id, ch in plugin.channels.items():
                # Determine EventType from channel direction
                direction_str = ch.direction.value if hasattr(ch.direction, "value") else str(ch.direction)
                if direction_str == "input":
                    event_type = "sensor"
                elif direction_str == "output":
                    event_type = "actuator"
                else:
                    event_type = "range"

                # Auto-create an Event for this channel
                event_name = f"{data.instance_name} – {ch.name}"
                event_public_id = str(uuid.uuid4())
                event = Event(
                    public_id=event_public_id,
                    name=event_name,
                    min_value=ch.min_value,
                    max_value=ch.max_value,
                    unit=ch.unit,
                    type=event_type,
                    user_public_id=current_user.public_id,
                )
                db.add(event)

                mapping = ChannelMapping(
                    public_id=str(uuid.uuid4()),
                    plugin_instance_id=instance.id,
                    channel_id=ch_id,
                    channel_name=ch.name,
                    direction=ch.direction.value,
                    unit=ch.unit,
                    event_public_id=event_public_id,
                )
                db.add(mapping)
    except Exception:
        logger.exception("channel_auto_discovery_failed", plugin_id=data.plugin_id)

    return StatusResponse(status="success", message="Plugin instance created.")


@router.get("/{public_id}", response_model=PluginInstanceResponse)
async def get_plugin_instance(
    public_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> PluginInstanceResponse:
    result = await db.execute(
        select(PluginInstance)
        .where(PluginInstance.public_id == public_id)
        .options(selectinload(PluginInstance.channel_mappings))
    )
    instance = result.scalar_one_or_none()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plugin instance not found.")
    return PluginInstanceResponse.model_validate(instance)


@router.put("/{public_id}", response_model=StatusResponse)
async def update_plugin_instance(
    public_id: str,
    data: PluginInstanceUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> StatusResponse:
    return await update_from_schema(db, PluginInstance, public_id, data, entity_name="Plugin instance")


@router.delete("/{public_id}", response_model=StatusResponse)
async def delete_plugin_instance(
    public_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> StatusResponse:
    instance = await get_or_404(db, PluginInstance, public_id, entity_name="Plugin instance")

    # Collect event IDs linked via channel mappings
    result = await db.execute(
        select(ChannelMapping).where(ChannelMapping.plugin_instance_id == instance.id),
    )
    event_public_ids: list[str] = []
    for mapping in result.scalars().all():
        if mapping.event_public_id:
            event_public_ids.append(mapping.event_public_id)
            mapping.event_public_id = None  # Clear FK before deleting events

    if event_public_ids:
        await db.flush()

        # Detach dashboard widgets that reference these events
        widget_result = await db.execute(
            select(DashboardWidget).where(DashboardWidget.event_public_id.in_(event_public_ids)),
        )
        for widget in widget_result.scalars().all():
            widget.event_public_id = None

    return await delete_by_public_id(db, PluginInstance, public_id, entity_name="Plugin instance")


# ─── Channel mapping endpoints ──────────────────────────────────────────────


@router.get("/{public_id}/channels", response_model=list[ChannelMappingResponse])
async def list_channel_mappings(
    public_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> list[ChannelMappingResponse]:
    instance = await get_or_404(db, PluginInstance, public_id, entity_name="Plugin instance")
    result = await db.execute(select(ChannelMapping).where(ChannelMapping.plugin_instance_id == instance.id))
    return [ChannelMappingResponse.model_validate(m) for m in result.scalars().all()]


@router.post("/{public_id}/channels", response_model=StatusResponse, status_code=status.HTTP_201_CREATED)
async def create_channel_mapping(
    public_id: str,
    data: ChannelMappingCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> StatusResponse:
    instance = await get_or_404(db, PluginInstance, public_id, entity_name="Plugin instance")
    mapping = ChannelMapping(
        public_id=str(uuid.uuid4()),
        plugin_instance_id=instance.id,
        channel_id=data.channel_id,
        channel_name=data.channel_name,
        direction=data.direction,
        unit=data.unit,
        event_public_id=data.event_public_id,
    )
    db.add(mapping)
    return StatusResponse(status="success", message="Channel mapping created.")


@router.put("/{public_id}/channels/{mapping_id}", response_model=StatusResponse)
async def update_channel_mapping(
    public_id: str,
    mapping_id: str,
    data: ChannelMappingUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> StatusResponse:
    # Verify parent instance exists
    await get_or_404(db, PluginInstance, public_id, entity_name="Plugin instance")
    return await update_from_schema(db, ChannelMapping, mapping_id, data, entity_name="Channel mapping")


@router.delete("/{public_id}/channels/{mapping_id}", response_model=StatusResponse)
async def delete_channel_mapping(
    public_id: str,
    mapping_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> StatusResponse:
    await get_or_404(db, PluginInstance, public_id, entity_name="Plugin instance")
    return await delete_by_public_id(db, ChannelMapping, mapping_id, entity_name="Channel mapping")
