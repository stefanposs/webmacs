"""Plugin instance CRUD endpoints."""

from __future__ import annotations

import json
import uuid

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from webmacs_backend.dependencies import AdminUser, DbSession, ViewerUser
from webmacs_backend.models import ChannelMapping, Event, PluginInstance
from webmacs_backend.repository import ConflictError, get_or_404, paginate, update_from_schema
from webmacs_backend.schemas import (
    PaginatedResponse,
    PluginInstanceCreate,
    PluginInstanceResponse,
    PluginInstanceUpdate,
    StatusResponse,
)
from webmacs_backend.services.plugin_service import delete_plugin_cascade

router = APIRouter()
logger = structlog.get_logger()


@router.get("/", response_model=PaginatedResponse[PluginInstanceResponse])
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


@router.post("/", response_model=StatusResponse, status_code=status.HTTP_201_CREATED)
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
                    # Determine EventType from channel direction
                    direction_str = ch.direction.value if hasattr(ch.direction, "value") else str(ch.direction)
                    if direction_str == "input":
                        event_type = "sensor"
                    elif direction_str == "output":
                        event_type = "actuator"
                    else:
                        event_type = "range"

                    # Auto-create or reuse an Event for this channel
                    event_name = f"{data.instance_name} – {ch.name}"
                    existing_event = await db.execute(
                        select(Event).where(Event.name == event_name),
                    )
                    existing = existing_event.scalar_one_or_none()

                    if existing:
                        # Reuse orphaned event from a previous instance
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


@router.get("/{public_id}", response_model=PluginInstanceResponse)
async def get_plugin_instance(
    public_id: str,
    db: DbSession,
    current_user: ViewerUser,
) -> PluginInstanceResponse:
    """Retrieve a single plugin instance by public ID."""
    result = await db.execute(
        select(PluginInstance)
        .where(PluginInstance.public_id == public_id)
        .options(selectinload(PluginInstance.channel_mappings)),
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
    current_user: AdminUser,
) -> StatusResponse:
    """Update a plugin instance's configuration."""
    return await update_from_schema(db, PluginInstance, public_id, data, entity_name="Plugin instance")


@router.delete("/{public_id}", response_model=StatusResponse)
async def delete_plugin_instance(
    public_id: str,
    db: DbSession,
    current_user: AdminUser,
) -> StatusResponse:
    """Delete a plugin instance and all associated channel mappings."""
    instance = await get_or_404(db, PluginInstance, public_id, entity_name="Plugin instance")
    await delete_plugin_cascade(db, instance)
    return StatusResponse(status="success", message="Plugin instance successfully deleted.")
