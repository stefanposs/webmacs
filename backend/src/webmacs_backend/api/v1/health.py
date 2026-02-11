"""Rich health endpoint — returns status of database, controller, and last sensor read."""

from __future__ import annotations

import datetime
import time
from typing import TYPE_CHECKING

import structlog
from fastapi import APIRouter
from sqlalchemy import select, text

from webmacs_backend import __version__
from webmacs_backend.dependencies import DbSession
from webmacs_backend.models import Datapoint
from webmacs_backend.schemas import HealthResponse

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
logger = structlog.get_logger()

# ─── Startup time tracking ───────────────────────────────────────────────────

_start_time: float = time.monotonic()


def reset_start_time() -> None:
    """Reset uptime counter (called on app startup)."""
    global _start_time  # noqa: PLW0603
    _start_time = time.monotonic()


# ─── Health Check ────────────────────────────────────────────────────────────


async def _check_database(db: AsyncSession) -> str:
    """Ping the database. Returns 'ok' or 'error'."""
    try:
        await db.execute(text("SELECT 1"))
        return "ok"
    except Exception as exc:
        logger.error("Health check: database unreachable", error=str(exc))
        return "error"


async def _get_last_datapoint_time(db: AsyncSession) -> datetime.datetime | None:
    """Get timestamp of the most recent datapoint, or None."""
    try:
        result = await db.execute(select(Datapoint.timestamp).order_by(Datapoint.timestamp.desc()).limit(1))
        return result.scalar_one_or_none()
    except Exception:
        return None


@router.get("", response_model=HealthResponse)
async def health_check(db: DbSession) -> HealthResponse:
    """Rich health endpoint — no authentication required.

    Returns status of:
    - Database connectivity
    - Last datapoint timestamp
    - Application uptime
    """
    db_status = await _check_database(db)
    last_dp = await _get_last_datapoint_time(db)
    uptime = time.monotonic() - _start_time

    overall = "ok" if db_status == "ok" else "degraded"

    return HealthResponse(
        status=overall,
        version=__version__,
        database=db_status,
        last_datapoint=last_dp,
        uptime_seconds=round(uptime, 1),
    )
