"""Plugin management router — aggregates discovery, packages, instances, and channels.

Sub-modules:
- available.py  — GET /available   (plugin class discovery via entry_points)
- packages.py   — /packages CRUD   (wheel upload, list, uninstall)
- instances.py  — /{id} CRUD       (plugin instance get/update/delete)
- channels.py   — /{id}/channels   (channel mapping CRUD)

The list (GET "") and create (POST "") instance routes are registered directly
here because FastAPI disallows empty paths in included sub-routers.
"""

from __future__ import annotations

import json
import uuid

import structlog
from fastapi import APIRouter, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from webmacs_backend.dependencies import AdminUser, DbSession, ViewerUser
from webmacs_backend.models import ChannelMapping, Event, PluginInstance
from webmacs_backend.repository import ConflictError, paginate
from webmacs_backend.schemas import (
    PaginatedResponse,
    PluginInstanceCreate,
    PluginInstanceResponse,
    StatusResponse,
)

from .available import router as available_router
from .channels import router as channels_router
from .instances import router as instances_router
from .packages import router as packages_router

router = APIRouter()
logger = structlog.get_logger()

# NOTE: packages_router (prefix=/packages) MUST be included before instances_router
# to prevent FastAPI from matching "packages" as a /{public_id} path parameter.
router.include_router(available_router)
router.include_router(packages_router)


# ─── Plugin instance list & create (empty-path routes) ──────────────────────
# FastAPI disallows empty-path routes in included sub-routers, so these two
# root routes are defined directly on the aggregate router.


@router.get("", response_model=PaginatedResponse[PluginInstanceResponse])
async def list_plugin_instances(
    db: DbSession,
    current_user: ViewerUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> PaginatedResponse[PluginInstanceResponse]:
    """List all plugin instances with pagination."""
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
    current_user: AdminUser,
) -> StatusResponse:
    """Create a new plugin instance and optionally auto-discover channels."""
    result = await db.execute(
        select(PluginInstance).where(PluginInstance.instance_name == data.instance_name),
    )
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

    # Auto-discover channels from the plugin class and create mappings
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
                event_public_id: str | None = None

                if data.auto_create_events:
                    direction_str = ch.direction.value if hasattr(ch.direction, "value") else str(ch.direction)
                    if direction_str == "input":
                        event_type = "sensor"
                    elif direction_str == "output":
                        event_type = "actuator"
                    else:
                        event_type = "range"

                    event_name = f"{data.instance_name} – {ch.name}"
                    existing_event = await db.execute(
                        select(Event).where(Event.name == event_name),
                    )
                    existing = existing_event.scalar_one_or_none()

                    if existing:
                        event_public_id = existing.public_id
                        logger.info(
                            "reusing_existing_event",
                            event_name=event_name,
                            event_public_id=event_public_id,
                        )
                    else:
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


# ─── Include /{public_id} and channel routes ─────────────────────────────────
router.include_router(instances_router)
router.include_router(channels_router)

__all__ = ["router"]
