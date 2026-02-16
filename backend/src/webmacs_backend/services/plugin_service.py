"""Plugin lifecycle service — handles complex multi-table operations.

Extracted from the plugin router to improve testability and maintainability.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from sqlalchemy import delete, select

from webmacs_backend.models import ChannelMapping, DashboardWidget, Datapoint, Event, PluginInstance, Rule

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


async def delete_plugin_cascade(db: AsyncSession, instance: PluginInstance) -> None:
    """Delete a plugin instance and clean up all related data.

    Performs the following steps atomically within the caller's transaction:
    1. Collect event IDs linked via channel mappings
    2. Clear event FK on channel mappings (prevents FK violation)
    3. Delete Rules that reference these events (non-nullable FK)
    4. Detach DashboardWidgets from these events (nullable FK → set NULL)
    5. Bulk-delete Datapoints referencing these events
    6. Delete the Events themselves
    7. Delete the PluginInstance (cascades to ChannelMappings via ORM)
    """
    # Step 1: Collect event IDs from channel mappings
    result = await db.execute(
        select(ChannelMapping).where(ChannelMapping.plugin_instance_id == instance.id),
    )
    event_public_ids: list[str] = []
    for mapping in result.scalars().all():
        if mapping.event_public_id:
            event_public_ids.append(mapping.event_public_id)
            mapping.event_public_id = None  # Step 2: Clear FK

    if event_public_ids:
        await db.flush()

        # Step 3: Delete rules (non-nullable FK → events)
        await db.execute(
            delete(Rule).where(Rule.event_public_id.in_(event_public_ids)),
        )

        # Step 4: Detach dashboard widgets (nullable FK → set NULL)
        widget_result = await db.execute(
            select(DashboardWidget).where(DashboardWidget.event_public_id.in_(event_public_ids)),
        )
        for widget in widget_result.scalars().all():
            widget.event_public_id = None

        await db.flush()

        # Step 5: Bulk-delete datapoints
        await db.execute(
            delete(Datapoint).where(Datapoint.event_public_id.in_(event_public_ids)),
        )

        # Step 6: Delete events
        await db.execute(
            delete(Event).where(Event.public_id.in_(event_public_ids)),
        )

    # Step 7: Delete the instance itself (ORM cascade handles channel_mappings)
    await db.delete(instance)

    logger.info(
        "plugin_instance_deleted",
        instance_name=instance.instance_name,
        events_cleaned=len(event_public_ids),
    )
