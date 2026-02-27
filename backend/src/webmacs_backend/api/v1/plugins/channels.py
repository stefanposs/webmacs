"""Channel mapping endpoints for plugin instances."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, status
from sqlalchemy import select

from webmacs_backend.dependencies import AdminUser, DbSession, ViewerUser
from webmacs_backend.models import ChannelMapping, PluginInstance
from webmacs_backend.repository import delete_by_public_id, get_or_404, update_from_schema
from webmacs_backend.schemas import (
    ChannelMappingCreate,
    ChannelMappingResponse,
    ChannelMappingUpdate,
    StatusResponse,
)

router = APIRouter()
logger = structlog.get_logger()


@router.get("/{public_id}/channels", response_model=list[ChannelMappingResponse])
async def list_channel_mappings(
    public_id: str,
    db: DbSession,
    current_user: ViewerUser,
) -> list[ChannelMappingResponse]:
    """List all channel mappings for a plugin instance."""
    instance = await get_or_404(db, PluginInstance, public_id, entity_name="Plugin instance")
    result = await db.execute(
        select(ChannelMapping).where(ChannelMapping.plugin_instance_id == instance.id),
    )
    return [ChannelMappingResponse.model_validate(m) for m in result.scalars().all()]


@router.post(
    "/{public_id}/channels",
    response_model=StatusResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_channel_mapping(
    public_id: str,
    data: ChannelMappingCreate,
    db: DbSession,
    current_user: AdminUser,
) -> StatusResponse:
    """Create a new channel mapping for a plugin instance."""
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
    current_user: AdminUser,
) -> StatusResponse:
    """Update a channel mapping."""
    # Verify parent instance exists
    await get_or_404(db, PluginInstance, public_id, entity_name="Plugin instance")
    return await update_from_schema(db, ChannelMapping, mapping_id, data, entity_name="Channel mapping")


@router.delete("/{public_id}/channels/{mapping_id}", response_model=StatusResponse)
async def delete_channel_mapping(
    public_id: str,
    mapping_id: str,
    db: DbSession,
    current_user: AdminUser,
) -> StatusResponse:
    """Delete a channel mapping."""
    await get_or_404(db, PluginInstance, public_id, entity_name="Plugin instance")
    return await delete_by_public_id(db, ChannelMapping, mapping_id, entity_name="Channel mapping")
