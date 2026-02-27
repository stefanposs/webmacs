"""Experiments package - core endpoints and exports."""

from __future__ import annotations

from fastapi import APIRouter

from webmacs_backend.api.v1.experiments.core import router as core_router
from webmacs_backend.api.v1.experiments.export import router as export_router

# Export core router and attach export subrouter
router: APIRouter = core_router
router.include_router(export_router, prefix="", tags=["Experiment Exports"]) 
