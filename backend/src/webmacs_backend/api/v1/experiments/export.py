"""Experiment export endpoints (CSV)."""

from __future__ import annotations

import csv
import io
from collections.abc import Generator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from webmacs_backend.dependencies import DbSession, ViewerUser
from webmacs_backend.models import Datapoint, Event, Experiment
from webmacs_backend.repository import get_or_404

router = APIRouter()


@router.get("/{public_id}/export/csv")
async def export_experiment_csv(public_id: str, db: DbSession, current_user: ViewerUser) -> StreamingResponse:
    """Export all datapoints of an experiment as CSV."""
    exp = await get_or_404(db, Experiment, public_id, entity_name="Experiment")

    result = await db.execute(
        select(Datapoint, Event.name.label("event_name"), Event.unit)
        .join(Event, Datapoint.event_public_id == Event.public_id)
        .where(Datapoint.experiment_public_id == public_id)
        .order_by(Datapoint.timestamp)
    )
    rows = result.all()

    def generate() -> Generator[str]:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["timestamp", "event_name", "event_public_id", "value", "unit", "datapoint_public_id"])
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)

        for dp, event_name, unit in rows:
            writer.writerow(
                [
                    dp.timestamp.isoformat() if dp.timestamp else "",
                    event_name,
                    dp.event_public_id,
                    dp.value,
                    unit,
                    dp.public_id,
                ]
            )
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    safe_name = exp.name.replace(" ", "_").replace("/", "-")
    filename = f"experiment_{safe_name}_{public_id[:8]}.csv"

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
