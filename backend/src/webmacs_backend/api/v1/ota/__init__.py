"""OTA package - firmware update management and upload endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from webmacs_backend.api.v1.ota.core import router as core_router
from webmacs_backend.api.v1.ota.upload import router as upload_router

# Export core router as package router and attach upload subrouter
router: APIRouter = core_router
router.include_router(upload_router, prefix="", tags=["OTA Uploads"]) 
