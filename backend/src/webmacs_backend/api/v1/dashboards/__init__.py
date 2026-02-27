"""Dashboards package - aggregates core and widget routers."""

from __future__ import annotations

from fastapi import APIRouter  # noqa: TC002

from webmacs_backend.api.v1.dashboards.core import router as core_router
from webmacs_backend.api.v1.dashboards.widgets import router as widgets_router

# Export the core router as the package router to avoid empty-prefix conflicts
router: APIRouter = core_router
router.include_router(widgets_router, prefix="", tags=["Dashboard Widgets"])
