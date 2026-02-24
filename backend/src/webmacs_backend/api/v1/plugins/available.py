"""Plugin discovery endpoints — list available installed plugin classes."""

from __future__ import annotations

import structlog
from fastapi import APIRouter

from webmacs_backend.dependencies import ViewerUser
from webmacs_backend.schemas import PluginMetaResponse

router = APIRouter()
logger = structlog.get_logger()


@router.get("/available", response_model=list[PluginMetaResponse])
async def list_available_plugins(current_user: ViewerUser) -> list[PluginMetaResponse]:
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
