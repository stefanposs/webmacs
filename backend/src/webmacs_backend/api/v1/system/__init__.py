"""System-level endpoints (versions, update triggers)."""

from __future__ import annotations

from fastapi import APIRouter

from webmacs_backend.api.v1.system.versions import router as versions_router

router: APIRouter = APIRouter()
router.include_router(versions_router, prefix="", tags=["System"])
