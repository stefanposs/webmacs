"""Datapoint endpoints."""

from __future__ import annotations

import asyncio
import datetime
import uuid

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import desc, func, insert, select

from webmacs_backend.dependencies import CurrentUser, DbSession
from webmacs_backend.enums import WebhookEventType
from webmacs_backend.models import Datapoint, Event, Experiment
from webmacs_backend.repository import delete_by_public_id, get_or_404
from webmacs_backend.schemas import (
    DatapointBatchCreate,
    DatapointCreate,
    DatapointResponse,
    DatapointSeriesRequest,
    PaginatedResponse,
    StatusResponse,
)
from webmacs_backend.services import build_payload, dispatch_event
from webmacs_backend.services.rule_evaluator import evaluate_rules_for_datapoint
from webmacs_backend.ws.connection_manager import manager

logger = structlog.get_logger()

router = APIRouter()

# Store background tasks so they aren't garbage-collected (RUF006)
_background_tasks: set[asyncio.Task[None]] = set()


async def _active_experiment_id(db: DbSession) -> str | None:
    """Return the public_id of the currently running experiment, or None."""
    result = await db.execute(select(Experiment.public_id).where(Experiment.stopped_on.is_(None)))
    row = result.first()
    return row[0] if row else None


def _fire_webhook_for_datapoint(event_public_id: str, value: float) -> None:
    """Schedule a fire-and-forget webhook dispatch for a new datapoint."""
    payload = build_payload(
        WebhookEventType.sensor_reading,
        sensor=event_public_id,
        value=value,
    )
    task = asyncio.create_task(dispatch_event(WebhookEventType.sensor_reading, payload))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


@router.get("", response_model=PaginatedResponse[DatapointResponse])
async def list_datapoints(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> PaginatedResponse[DatapointResponse]:
    total = (await db.execute(select(func.count(Datapoint.id)))).scalar_one()
    result = await db.execute(
        select(Datapoint).order_by(desc(Datapoint.timestamp)).offset((page - 1) * page_size).limit(page_size)
    )
    return PaginatedResponse(
        page=page,
        page_size=page_size,
        total=total,
        data=[DatapointResponse.model_validate(dp) for dp in result.scalars().all()],
    )


@router.post("", response_model=StatusResponse, status_code=status.HTTP_201_CREATED)
async def create_datapoint(data: DatapointCreate, db: DbSession, current_user: CurrentUser) -> StatusResponse:
    event_result = await db.execute(select(Event.public_id).where(Event.public_id == data.event_public_id))
    if not event_result.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")

    exp_id = await _active_experiment_id(db)
    db.add(
        Datapoint(
            public_id=str(uuid.uuid4()),
            value=data.value,
            timestamp=datetime.datetime.now(datetime.UTC),
            event_public_id=data.event_public_id,
            experiment_public_id=exp_id,
        )
    )
    _fire_webhook_for_datapoint(data.event_public_id, data.value)
    try:
        await evaluate_rules_for_datapoint(db, data.event_public_id, data.value)
    except Exception:
        logger.exception("Rule evaluation failed — datapoint saved, rules skipped")

    # Broadcast to frontend WebSocket subscribers
    now_iso = datetime.datetime.now(datetime.UTC).isoformat()
    await manager.broadcast(
        "frontend",
        {
            "type": "datapoints_batch",
            "datapoints": [
                {
                    "value": data.value,
                    "event_public_id": data.event_public_id,
                    "timestamp": now_iso,
                    "experiment_public_id": exp_id,
                }
            ],
        },
    )

    return StatusResponse(status="success", message="Datapoint successfully created.")


@router.post("/batch", response_model=StatusResponse, status_code=status.HTTP_201_CREATED)
async def create_datapoints_batch(
    data: DatapointBatchCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> StatusResponse:
    exp_id = await _active_experiment_id(db)
    now = datetime.datetime.now(datetime.UTC)

    rows = [
        {
            "public_id": str(uuid.uuid4()),
            "value": dp.value,
            "timestamp": now,
            "event_public_id": dp.event_public_id,
            "experiment_public_id": exp_id,
        }
        for dp in data.datapoints
    ]
    if rows:
        await db.execute(insert(Datapoint), rows)
        # Fire webhook for each datapoint in batch (fire-and-forget)
        for dp in data.datapoints:
            _fire_webhook_for_datapoint(dp.event_public_id, dp.value)
            try:
                await evaluate_rules_for_datapoint(db, dp.event_public_id, dp.value)
            except Exception:
                logger.exception("Rule evaluation failed — datapoint saved, rules skipped")

        # Broadcast to frontend WebSocket subscribers
        await manager.broadcast(
            "frontend",
            {
                "type": "datapoints_batch",
                "datapoints": [
                    {
                        "value": dp.value,
                        "event_public_id": dp.event_public_id,
                        "timestamp": now.isoformat(),
                        "experiment_public_id": exp_id,
                    }
                    for dp in data.datapoints
                ],
            },
        )

    return StatusResponse(status="success", message=f"{len(rows)} datapoints successfully created.")


@router.post("/series", response_model=dict[str, list[DatapointResponse]])
async def get_datapoint_series(
    data: DatapointSeriesRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict[str, list[DatapointResponse]]:
    """Return recent datapoints grouped by event_public_id (for dashboard charts)."""
    cutoff = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=data.minutes)
    result = await db.execute(
        select(Datapoint)
        .where(Datapoint.event_public_id.in_(data.event_public_ids), Datapoint.timestamp >= cutoff)
        .order_by(Datapoint.timestamp)
    )
    series: dict[str, list[DatapointResponse]] = {eid: [] for eid in data.event_public_ids}
    for dp in result.scalars().all():
        if dp.event_public_id in series:
            series[dp.event_public_id].append(DatapointResponse.model_validate(dp))
    return series


@router.get("/latest", response_model=list[DatapointResponse])
async def get_latest_datapoints(db: DbSession, current_user: CurrentUser) -> list[DatapointResponse]:
    # Subquery: for each event, find the max id among the rows with the latest timestamp.
    ts_subq = (
        select(Datapoint.event_public_id, func.max(Datapoint.timestamp).label("max_ts"))
        .group_by(Datapoint.event_public_id)
        .subquery()
    )
    id_subq = (
        select(func.max(Datapoint.id).label("max_id"))
        .join(
            ts_subq,
            (Datapoint.event_public_id == ts_subq.c.event_public_id) & (Datapoint.timestamp == ts_subq.c.max_ts),
        )
        .group_by(Datapoint.event_public_id)
        .subquery()
    )
    result = await db.execute(select(Datapoint).where(Datapoint.id.in_(select(id_subq.c.max_id))))
    return [DatapointResponse.model_validate(dp) for dp in result.scalars().all()]


@router.get("/{public_id}", response_model=DatapointResponse)
async def get_datapoint(public_id: str, db: DbSession, current_user: CurrentUser) -> DatapointResponse:
    dp = await get_or_404(db, Datapoint, public_id, entity_name="Datapoint")
    return DatapointResponse.model_validate(dp)


@router.delete("/{public_id}", response_model=StatusResponse)
async def delete_datapoint(public_id: str, db: DbSession, current_user: CurrentUser) -> StatusResponse:
    return await delete_by_public_id(db, Datapoint, public_id, entity_name="Datapoint")
