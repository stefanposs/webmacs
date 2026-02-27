"""Monitoring endpoints (lightweight metrics)."""
from __future__ import annotations

from fastapi import APIRouter

from webmacs_backend.services.metrics import snapshot as metrics_snapshot

router = APIRouter()


@router.get("/metrics")
async def get_metrics() -> dict:
    """Return a JSON snapshot of runtime metrics.

    This is intentionally simple (not Prometheus) to keep dependencies low
    and to serve CI/debugging needs.
    """
    return metrics_snapshot()
