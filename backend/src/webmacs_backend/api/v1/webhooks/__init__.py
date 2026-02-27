"""Webhooks package - aggregates core and delivery routers."""

from __future__ import annotations

from fastapi import APIRouter  # noqa: TC002

from webmacs_backend.api.v1.webhooks.core import router as core_router
from webmacs_backend.api.v1.webhooks.deliveries import router as deliveries_router

# Export core router as package router and attach deliveries router
router: APIRouter = core_router
router.include_router(deliveries_router, prefix="", tags=["Webhook Deliveries"])
